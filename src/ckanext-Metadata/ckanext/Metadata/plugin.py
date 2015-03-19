# {% set dataset_is_draft = data.get('state', 'draft').startswith('draft') or data.get('state', 'none') ==  'none' %}
#   {% set dataset_has_organization = data.owner_org or data.group_id %}

from logging import getLogger
import ckan.plugins as p
import formencode.validators as v
import ckan.new_authz as auth
import copy
from ckan.logic.action.create import user_create as core_user_create, package_create
from ckan.logic.action.update import package_update
from ckan.logic.action.get import user_show, package_show
import ckan.lib.dictization.model_dictize as model_dictize
import ckan.lib.helpers as h
import helpers as meta_helper
import os

log = getLogger(__name__)

#excluded title, description, tags and last update as they're part of the default ckan dataset metadata
required_metadata = (
                     {'id': 'language', 'validators': [v.String(max=100)]},
                     
                     {'id': 'data_type', 'validators': [v.String(max=100)]},
                     {'id': 'access_information', 'validators': [v.String(max=500)]},   # use_constraints
                     {'id': 'status', 'validators': [v.String(max=100)]},
)

#optional metadata
expanded_metadata = (
                        {'id': 'spatial', 'validators': [v.String(max=500)]},
                        {'id': 'temporal', 'validators': [v.String(max=300)]},
                        {'id': 'purpose', 'validators': [v.String(max=100)]},
                        {'id': 'research_focus', 'validators': [v.String(max=50)]},

                        {'id': 'sub_name', 'validators': [v.String(max=100)]},
                        {'id': 'sub_email', 'validators': [v.String(max=100)]},
                        {'id': 'license_id', 'validators': [v.String(max=50)]},
                        {'id': 'version', 'validators': [v.String(max=50)]},

                        {'id': 'feature_types', 'validators': [v.String(max=100)]},
                        {'id': 'north_extent', 'validators': [v.String(max=100)]},
                        {'id': 'south_extent', 'validators': [v.String(max=100)]},
                        {'id': 'east_extent', 'validators': [v.String(max=100)]},
                        {'id': 'west_extent', 'validators': [v.String(max=100)]},
                        {'id': 'horz_coord_system', 'validators': [v.String(max=100)]},
                        {'id': 'vert_coord_system', 'validators': [v.String(max=100)]},

                        {'id': 'update_frequency', 'validators': []},
                        {'id': 'study_area', 'validators': [v.String(max=100)]},
                        {'id': 'data_processing_method', 'validators': [v.String(max=500)]},
                        {'id': 'data_collection_method', 'validators': [v.String(max=500)]},
                        {'id': 'citation', 'validators': [v.String(max=500)]},
                        {'id': 'required_software', 'validators': [v.String(max=100)]},

)


# needed for repeatable data elements
def creator_schema():
    ignore_missing = p.toolkit.get_validator('ignore_missing')
    not_empty = p.toolkit.get_validator('not_empty')

    schema = {
        'name': [not_empty, convert_to_extras_custom],
        'email': [ignore_missing, convert_to_extras_custom],
        'phone': [ignore_missing, convert_to_extras_custom],
        'address': [ignore_missing, convert_to_extras_custom],
        'organization': [ignore_missing, convert_to_extras_custom],
        'is_a_group': [ignore_missing, convert_to_extras_custom],
        'delete': [ignore_missing, convert_to_extras_custom]
    }

    return schema


# needed for repeatable data elements
def contributor_schema():
    ignore_missing = p.toolkit.get_validator('ignore_missing')
    not_empty = p.toolkit.get_validator('not_empty')

    schema = {
        'name': [not_empty, convert_to_extras_custom],
        'email': [ignore_missing, convert_to_extras_custom],
        'phone': [ignore_missing, convert_to_extras_custom],
        'address': [ignore_missing, convert_to_extras_custom],
        'organization': [ignore_missing, convert_to_extras_custom],
        'delete': [ignore_missing, convert_to_extras_custom]
    }

    return schema


# needed for repeatable data elements
def variable_schema():
    ignore_missing = p.toolkit.get_validator('ignore_missing')
    not_empty = p.toolkit.get_validator('not_empty')

    schema = {
        'name': [not_empty, convert_to_extras_custom],
        'unit': [not_empty, convert_to_extras_custom],
        'delete': [ignore_missing, convert_to_extras_custom]
    }

    return schema


# needed for repeatable data elements
def convert_to_extras_custom(key, data, errors, context):

    #    print "key :====> ", key, "data : ====>", data[key]
    extras = data.get(('extras',), [])

    if not extras:
        data[('extras',)] = extras

    keyStr = ':'.join([str(x) for x in key])

    extras.append({'key': keyStr, 'value': data[key]})


# needed for repeatable data elements
def convert_from_extras(key, data, errors, context):
    print "key : <====", key, "\n"

    def remove_from_extras(data, keyList):
        to_remove = []
        for data_key, data_value in data.iteritems():
            if data_key[0] == 'extras' and data_key[1] in keyList:
                to_remove.append(data_key)

        for item in to_remove:
            del data[item]

    indexList = []  # A list containing the index of items in extras to be removed.
    new_data = {}   # A new dictionary for data stored in extras with the given key

    for data_key, data_value in data.iteritems():
        if data_key[0] == 'extras' and data_key[-1] == 'key':
            #Extract the key components separated by ':'
            keyList = data_value.split(':')

            #Check for multiple value inputs and convert the list item index to integer
            if len(keyList) > 1:
                    keyList[1] = int(keyList[1])

            #Construct the key for the stored value(s)
            newKey = tuple(keyList)

            if key[-1] == newKey[0]:
                #Retrieve data from extras and add it to new_data so it can be added to the data dictionary.
                new_data[newKey] = data[('extras', data_key[1], 'value')]

                #Add the data index in extras to the list of items to be removed.
                indexList.append(data_key[1])

    #Remove all data from extras with the given index
    remove_from_extras(data, indexList)
    #Remove previous data stored under the given key
    del data[key]

    # get rid of all repeatable elements if they are marked as deleted (delete = '1')
    deleteIndex_creators = []
    deleteIndex_contributors = []
    deleteIndex_variables = []

    for data_key, data_value in new_data.iteritems():
        #If this is a deleted record then add it to the deleted list to be removed from data later.
        if 'delete' in data_key and data_value == '1':
            if 'creators' == data_key[0]:
                deleteIndex_creators.append(data_key[1])
            elif 'contributors' == data_key[0]:
                deleteIndex_contributors.append(data_key[1])
            elif 'variables' == data_key[0]:
                deleteIndex_variables.append(data_key[1])

    deleted = []

    for data_key, data_value in new_data.iteritems():
        if len(data_key) > 1:
            if data_key[0] == 'creators' and data_key[1] in deleteIndex_creators:
                deleted.append(data_key)
            elif data_key[0] == 'contributors' and data_key[1] in deleteIndex_contributors:
                deleted.append(data_key)
            elif data_key[0] == 'variables' and data_key[1] in deleteIndex_variables:
                deleted.append(data_key)

    for item in deleted:
        del new_data[item]

    #Add data extracted from extras to the data dictionary
    for data_key, data_value in new_data.iteritems():
        data[data_key] = data_value


# TODO: the following method is not used
def _process_deleted_repeatables(data_dict, deleted_indexes, repeatable_name):
    # removes all deleted repeatable elements form the data_dict
    # param: data_dict from which keys to be removed
    # param: deleted_indexes a list of indexes for the specified repeatable element
    # param: repeatable_element name of the repeatable element

    last_used_deleted_index = 0
    index_to_adjust = 0
    keys_to_delete = []
    new_data_to_add = []

    if len(deleted_indexes) > 0:
        for data_key, data_value in data_dict.iteritems():
            if len(data_key) > 1 and data_key[0] == repeatable_name:
                if data_key[1] > min(deleted_indexes) and data_key[1] != 0:
                    if index_to_adjust != 0 and index_to_adjust != data_key[1]:
                        del deleted_indexes[last_used_deleted_index]
                    if index_to_adjust == data_key[1]:
                        new_data_key = (data_key[0], min(deleted_indexes), data_key[2])
                        new_data_to_add.append({new_data_key: data_dict[data_key]})
                        keys_to_delete.append(data_key)
                    else:
                        index_to_adjust = data_key[1]
                        last_used_deleted_index = min(deleted_indexes)
                        new_data_key = (data_key[0], last_used_deleted_index, data_key[2])
                        new_data_to_add.append({new_data_key: data_dict[data_key]})
                        keys_to_delete.append(data_key)

        for key in keys_to_delete:
            del data_dict[key]

        for dict_item in new_data_to_add:
            for key, value in dict_item.iteritems():
                data_dict[key] = value
                break


#add validator 'not-empty' for all required metadata fields
def get_req_metadata_for_create():
    new_req_meta = copy.deepcopy(required_metadata)
    validator = p.toolkit.get_validator('not_empty')
    for meta in new_req_meta:
        meta['validators'].append(validator)
    return new_req_meta


# adds validator 'ignore-missing' for all optional metadata fields
def get_req_metadata_for_show_update():
    new_req_meta = copy.deepcopy(required_metadata)
    validator = p.toolkit.get_validator('ignore_missing')
    for meta in new_req_meta:
        meta['validators'].append(validator)
    return new_req_meta

for meta in expanded_metadata:
    meta['validators'].append(p.toolkit.get_validator('ignore_missing'))

schema_updates_for_create = [{meta['id']: meta['validators']+[p.toolkit.get_converter('convert_to_extras')]}
                             for meta in (get_req_metadata_for_create() + expanded_metadata)]

schema_updates_for_show = [{meta['id']: [p.toolkit.get_converter('convert_from_extras')] + meta['validators']}
                           for meta in (get_req_metadata_for_show_update() + expanded_metadata)]


class MetadataPlugin(p.SingletonPlugin, p.toolkit.DefaultDatasetForm):
    '''This plugin adds fields for the metadata (known as the Common Core) defined at
    https://github.com/project-open-data/project-open-data.github.io/blob/master/schema.md
    '''

    p.implements(p.ITemplateHelpers)
    p.implements(p.IConfigurer)
    p.implements(p.IDatasetForm)
    p.implements(p.IActions)
    p.implements(p.IPackageController, inherit=True)

    p.toolkit.add_resource('public', 'metadata_resources')

    # template helper function
    @classmethod
    def check_if_user_owns_dataset(cls, package_id, username):
        return meta_helper.is_user_owns_package(package_id, username)

    # template helper function
    @classmethod
    def get_pylons_context_obj(cls):
        """
        This one will allow us to access the c object in a snippet template
        """
        return p.toolkit.c

    # template helper function
    @classmethod
    def has_user_group_or_org_admin_role(cls, group_id, user_name):
        """
        Checks if the given user has admin role for the specified group/org
        """
        return auth.has_user_permission_for_group_or_org(group_id, user_name, 'admin')

    # template helper function
    @classmethod
    def load_data_into_dict(cls, data_dict):
        '''
        a jinja2 template helper function.
        'extras' contains a list of dicts corresponding to the extras used to store arbitrary key value pairs in CKAN.
        This function moves each entry in 'extras' that is a common core metadata into 'custom_meta'

        Example:
        {'hi':'there', 'extras':[{'key': 'publisher', 'value':'USGS'}]}
        becomes
        {'hi':'there', 'custom_meta':{'publisher':'USGS'}, 'extras':[]}

        '''

        new_dict = copy.deepcopy(data_dict)
        common_metadata = [x['id'] for x in required_metadata+expanded_metadata]

        # needed for repeatable metadata
        # the original data_dict will have the creator set of data keys as follows:
        # creators:0:name # for creator#1
        # creators:0:email
        # creators:0:phone
        # creators:0:address
        # creators:0:organization
        # creators:0:is_a_group

        # creators:1:name # for creator#2
        # creators:1:email
        # creators:1:phone
        # creators:1:address
        # creators:1:organization
        # creators:1:is_a_group
        #
        # In the generated new new_dict we want the set of creator data as follows:
        # new_dict['custom_meta']['creators'] = [
        #                           {'name': name1-value, 'email': email1-value, 'phone': phone1-value, 'address': address1-value, 'organization': org1-value}
        #                           {'name': name2-value, 'email': email2-value, 'phone': phone2-value, 'address': address2-value, 'organization': org2-value}
        #                           { .......}
        #                        ]
        # the same logic above applies to any other repeatable element that we have in the schema

        try:
            new_dict['custom_meta']
        except KeyError:
            new_dict['custom_meta'] = {}

        repeatable_elements = ['creators', 'contributors', 'variables']
        for element in repeatable_elements:
            new_dict['custom_meta'][element] = []

        reduced_extras = []

        sub_name = ''
        sub_email = ''
        try:
            for extra in new_dict['extras']:
                if extra['key'] in common_metadata:
                    new_dict['custom_meta'][extra['key']] = extra['value']
                    # grab the submitter name and email to set default first creator name and email
                    if extra['key'] == 'sub_name':
                        sub_name = extra['value']
                    if extra['key'] == 'sub_email':
                        sub_email = extra['value']
                else:
                    # check if the key matches the any of the repeatable metadata element
                    data_key_parts = extra['key'].split(':')
                    if data_key_parts[0] not in repeatable_elements or len(data_key_parts) != 3:
                        reduced_extras.append(extra)

            # repeatable element key shorting is necessary so that a key like 'creators:10:name"
            # does not come before a key like 'creators:2:name'
            sorted_creator_keys = cls._get_sorted_repeatable_element_keys(new_dict['extras'], 'creators')
            sorted_contributor_keys = cls._get_sorted_repeatable_element_keys(new_dict['extras'], 'contributors')
            sorted_variable_keys = cls._get_sorted_repeatable_element_keys(new_dict['extras'], 'variables')

            cls._load_repeatable_elements_to_dict(new_dict, sorted_creator_keys, new_dict['extras'])
            cls._load_repeatable_elements_to_dict(new_dict, sorted_contributor_keys, new_dict['extras'])
            cls._load_repeatable_elements_to_dict(new_dict, sorted_variable_keys, new_dict['extras'])

            # add the default creator if no creator exists at this point
            set_default_creator(new_dict, sub_name, sub_email)

            new_dict['extras'] = reduced_extras

        except KeyError as ex:
            log.debug('''Expected key ['%s'] not found, attempting to move common core keys to subdictionary''',
                      ex.message)
            #this can happen when a form fails validation, as all the data will now be as key,value pairs, not under extras,
            #so we'll move them to the expected point again to fill in the values
            # e.g.
            # { 'foo':'bar','publisher':'somename'} becomes {'foo':'bar', 'custom_meta':{'publisher':'somename'}}

            keys_to_remove = []

            log.debug('common core metadata: {0}'.format(common_metadata))
            for key, value in new_dict.iteritems():
                #TODO remove debug
                log.debug('checking key: {0}'.format(key))
                if key in common_metadata:
                    #TODO remove debug
                    log.debug('adding key: {0}'.format(key))
                    new_dict['custom_meta'][key] = value
                    keys_to_remove.append(key)

                    # grab the submitter name and email to set default first creator name and email
                    if key == 'sub_name':
                        sub_name = value
                    if key == 'sub_email':
                        sub_email = value
                else:
                    # check if the key matches any of the repeatable metadata element
                    if key in repeatable_elements:
                        for repeat_item in value:
                            new_dict['custom_meta'][key].append(repeat_item)

            for key in keys_to_remove:
                del new_dict[key]

            # add the default creator if no creator exists at this point
            set_default_creator(new_dict, sub_name, sub_email)

        # remove any repeatable elements marked as deleted from the dict
        for element in repeatable_elements:
            valid_repeatables = [c for c in new_dict['custom_meta'][element] if c['delete'] != '1']
            new_dict['custom_meta'][element] = valid_repeatables

        return new_dict

    @classmethod
    def _load_repeatable_elements_to_dict(cls, dict_to_load_to, repeatable_element_keys, extra_data):
        for element_key in repeatable_element_keys:
                data_key_parts = element_key.split(':')
                element_dataset_index = int(data_key_parts[1])
                if element_dataset_index == len(dict_to_load_to['custom_meta'][data_key_parts[0]]):
                    element = {data_key_parts[2]: cls._get_extra_value(extra_data, element_key)}
                    dict_to_load_to['custom_meta'][data_key_parts[0]].append(element)
                else:
                    dict_to_load_to['custom_meta'][data_key_parts[0]][element_dataset_index][data_key_parts[2]] = \
                        cls._get_extra_value(extra_data, element_key)
        return dict_to_load_to

    @classmethod
    def _get_sorted_repeatable_element_keys(cls, extra_data, element_name):

        def get_key(item):
            # if the item is 'creators:0:name'
            # after the split we will have parts = ['creators', 0, 'name']
            parts = item.split(":")
            return int(parts[1])

        element_key_list = []
        for extra in extra_data:
            data_key_parts = extra['key'].split(':')
            if data_key_parts[0] == element_name and len(data_key_parts) == 3:
                element_key_list.append(extra['key'])

        return sorted(element_key_list, key=get_key)

    @classmethod
    def _get_extra_value(cls, extra_dict, key):
        for extra in extra_dict:
            if extra['key'] == key:
                return extra['value']

        return None

    def __create_vocabulary(cls, name, *values):
        '''Create vocab and tags, if they don't exist already.
            name: the name or unique id of the vocabulary  e.g. 'flower_colors'
            values: the values that the vocabulary can take on e.g. ('blue', 'orange', 'purple', 'white', 'yellow)
        '''
        user = p.toolkit.get_action('get_site_user')({'ignore_auth': True}, {})
        context = {'user': user['name']}

        log.debug("Creating vocab '{0}'".format(name))
        data = {'name': name}
        vocab = p.toolkit.get_action('vocabulary_create')(context, data)
        log.debug('Vocab created: {0}'.format(vocab))
        for tag in values:
            log.debug(
                "Adding tag {0} to vocab {1}'".format(tag, name))
            data = {'name': tag, 'vocabulary_id': vocab['id']}
            p.toolkit.get_action('tag_create')(context, data)
        return vocab

    @classmethod
    def __update_vocabulary(cls, name, *values):
        user = p.toolkit.get_action('get_site_user')({'ignore_auth': True}, {})
        context = {'user': user['name']}

        log.debug("Updating vocab '{0}'".format(name))
        data = {'id': name}
        vocab = p.toolkit.get_action('vocabulary_show')(context, data)
        data = {'name': name, 'id': vocab['id']}
        vocab = p.toolkit.get_action('vocabulary_update')(context, data)

        log.debug('Vocab updated: {0}'.format(vocab))
        for tag in values:
            log.debug(
                "Adding tag {0} to vocab {1}'".format(tag, name))
            data = {'name': tag, 'vocabulary_id': vocab['id']}
            p.toolkit.get_action('tag_create')(context, data)
        return vocab

    @classmethod
    def __add_tag_to_vocabulary(cls, name, *values):
        user = p.toolkit.get_action('get_site_user')({'ignore_auth': True}, {})
        context = {'user': user['name']}

        log.debug("Updating vocab '{0}'".format(name))
        data = {'id': name}
        vocab = p.toolkit.get_action('vocabulary_show')(context, data)

        log.debug('Vocab updated: {0}'.format(vocab))
        for tag in values:
            log.debug(
                "Adding tag {0} to vocab {1}'".format(tag, name))
            data = {'name': tag, 'vocabulary_id': vocab['id']}
            p.toolkit.get_action('tag_create')(context, data)

        data = {'id': name}
        vocab = p.toolkit.get_action('vocabulary_show')(context, data)
        return vocab

    # template helper function
    @classmethod
    def get_research_focus(cls):
        '''        log.debug('get_research_focus() called')
            Jinja2 template helper function, gets the vocabulary for research focus
        '''
        # NOTE: any time you want to include new tag for the vocabulary term 'research_focus' add the tag name
        # to the following list (research_focus_tags). Nothing else need to be changed
        research_focus_tags = [u'RFA1', u'RFA2', u'RFA3', u'other', u'CI', u'EOD']
        vocab_name = 'research_focus'
        research_focus = cls.__get_tags(vocab_name, research_focus_tags)
        return research_focus

    # template helper function
    @classmethod
    def get_update_frequency(cls):
        '''
        log.debug('get_update_frequency() called')
            Jinja2 template helper function, gets the vocabulary for update_frequency
        '''
        # NOTE: any time you want to include new tag for the vocabulary term 'update_frequency' add the tag name
        # to the following list. Nothing else need to be changed
        update_frequency_tags = ['none', 'real time', 'hourly', 'daily', 'weekly', 'monthly', 'yearly', 'other']
        vocab_name = 'update_frequency'
        update_frequency = cls.__get_tags(vocab_name, update_frequency_tags)
        return update_frequency

    # template helper function
    @classmethod
    def get_study_area(cls):
        '''        log.debug('get_study_area() called')
            Jinja2 template helper function, gets the vocabulary for access levels
        '''
        # NOTE: any time you want to include new tag for the vocabulary term 'study_area' add the tag name
        # to the following list (study_area_tags). Nothing else need to be changed
        study_area_tags = [u'other', u'WRMA-Wasatch Range Metropolitan Area', u'Logan River Watershed',
                           u'Red Butte Creek Watershed',  u'Provo River Watershed', u'Multiple Watersheds']
        vocab_name = 'study_area'
        study_area = cls.__get_tags(vocab_name, study_area_tags)
        return study_area

    # template helper function
    @classmethod
    def get_types(cls):
        '''        log.debug('type() called')
            Jinja2 template helper function, gets the vocabulary for type
        '''
        # NOTE: any time you want to include new tag for the vocabulary term 'type' add the tag name
        # to the following list (type_tags). Nothing else need to be changed
        type_tags = ['collection', 'dataset', 'image', 'interactive resource', 'model', 'service', 'software', 'text']
        vocab_name = 'type'
        types = cls.__get_tags(vocab_name, type_tags)
        return types

    # template helper function
    @classmethod
    def get_status(cls):
        '''        log.debug('get_study_area() called')
            Jinja2 template helper function, gets the vocabulary for status
        '''
        # NOTE: any time you want to include new tag for the vocabulary term 'status' add the tag name
        # to the following list (status_tags). Nothing else need to be changed
        status_tags = [u'complete', u'ongoing', u'planned', u'unknown']
        vocab_name = 'status'
        status = cls.__get_tags(vocab_name, status_tags)
        return status

    @classmethod
    def __get_tags(cls, vocab_name, tags):

        user = p.toolkit.get_action('get_site_user')({'ignore_auth': True}, {})
        context = {'user': user['name']}

        try:
            data = {'id': vocab_name}  # we can use the id or name for id param
            vocab = p.toolkit.get_action('vocabulary_show')(context, data)
            existing_tags = [tag['display_name'] for tag in vocab['tags']]
            # check if we need to create additional tags for this vocabulary term
            tags_to_add = [tag_name for tag_name in tags if tag_name not in existing_tags]
            if len(tags_to_add) > 0:
                vocab = cls.__add_tag_to_vocabulary(vocab_name, *tags_to_add)
        except:
            log.debug("vocabulary_show failed, meaning the vocabulary for %s doesn't exist", vocab_name)
            vocab = cls.__create_vocabulary(vocab_name, *tags)

        new_tags = [x['display_name'] for x in vocab['tags']]
        log.debug("vocab tags: %s" % new_tags)

        return new_tags


    #See ckan.plugins.interfaces.IDatasetForm
    def is_fallback(self):
        # Return False so that we use the CKAN's default for
        # /dataset/new and /dataset/edit
        return False
  
    #See ckan.plugins.interfaces.IDatasetForm
    def package_types(self):
        # This plugin doesn't handle any special package types, it just
        # registers itself as the default (above).

        return ['dataset']

    def package_form(self):
        return super(MetadataPlugin, self).package_form()

    #See ckan.plugins.interfaces.IDatasetForm
    def update_config(self, config):
        # Instruct CKAN to look in the ```templates``` directory for customized templates and snippets
        p.toolkit.add_template_directory(config, 'templates')

        # add the extension's public dir path so that
        # ckan can find any resources used from this path
        # get the current dir path (here) for this plugin
        here = os.path.dirname(__file__)
        rootdir = os.path.dirname(os.path.dirname(here))
        our_public_dir = os.path.join(rootdir, 'ckanext', 'Metadata', 'public')
        config['extra_public_paths'] = ','.join([our_public_dir, config.get('extra_public_paths', '')])

    #See ckan.plugins.interfaces.IDatasetForm
    def _modify_package_schema(self, schema):
        #log.debug("_modify_package_schema called")
        not_empty = p.toolkit.get_validator('not_empty')
        tag_string_convert = p.toolkit.get_validator('tag_string_convert')

        for update in schema_updates_for_create:
            schema.update(update)

        # update the ckan's tag_string element making it required - which would force the user to enter
        # at least on keyword (tag item)
        schema.update({'tag_string': [not_empty, tag_string_convert]})

        schema['resources']['name'][0] = not_empty

        schema.update({'creators': creator_schema()})   # needed for repeatable elements
        schema.update({'contributors': contributor_schema()})   # needed for repeatable elements
        schema.update({'variables': variable_schema()})   # needed for repeatable elements
        return schema

    #See ckan.plugins.interfaces.IDatasetForm
    def create_package_schema(self):
        log.debug('create_package_schema')
        schema = super(MetadataPlugin, self).create_package_schema()
        schema = self._modify_package_schema(schema)
        return schema

    #See ckan.plugins.interfaces.IDatasetForm
    def update_package_schema(self):
        #log.debug('update_package_schema')
        schema = super(MetadataPlugin, self).update_package_schema()
        schema = self._modify_package_schema(schema)

        return schema

    #See ckan.plugins.interfaces.IDatasetForm
    def show_package_schema(self):
        schema = super(MetadataPlugin, self).show_package_schema()
        ignore_missing = p.toolkit.get_validator('ignore_missing')
        # Don't show vocab tags mixed in with normal 'free' tags
        # (e.g. on dataset pages, or on the search page)
        schema['tags']['__extras'].append(p.toolkit.get_converter('free_tags_only'))

        for update in schema_updates_for_show:
            schema.update(update)

        schema.update({'creators': [convert_from_extras, ignore_missing]})  # needed for repeatable elements
        schema.update({'contributors': [convert_from_extras, ignore_missing]})  # needed for repeatable elements
        schema.update({'variables': [convert_from_extras, ignore_missing]})  # needed for repeatable elements
        return schema

    #Method below allows functions and other methods to be called from the Jinja template using the h variable
    def get_helpers(self):
        return {'get_research_focus': self.get_research_focus, 
                'required_metadata': required_metadata,
                'load_data_into_dict':  self.load_data_into_dict,
                'check_if_dataset_using_older_schema': check_if_dataset_using_older_schema,
                'study_area': self.get_study_area,
                'get_status': self.get_status,
                'get_types': self.get_types,
                'update_frequency': self.get_update_frequency,
                'check_if_user_owns_dataset': self.check_if_user_owns_dataset,
                'get_pylons_context_obj': self.get_pylons_context_obj,
                'has_user_group_or_org_admin_role': self.has_user_group_or_org_admin_role}

    #See ckan.plugins.interfaces.IActions    
    def get_actions(self):
        log.debug('get_actions() called') 
        return {
                 'package_create': pkg_create,
                 'package_update': pkg_update,
                 'user_create': user_create_local,
                 'user_show': show_user,
                 'package_show': show_package
        }

    # implements IPackageController
    def before_search(self, search_params):
        '''
            Extensions will receive a dictionary with the query parameters,
            and should return a modified (or not) version of it.

            search_params will include an `extras` dictionary with all values
            from fields starting with `ext_`, so extensions can receive user
            input from specific fields.

        '''
        # when listing datasets outside an organization, get only the
        # public (private:false) datasets
        if not 'owner_org' in search_params['q']:
            if len(search_params['q']) > 0:
                search_params['q'] += ' private:false'
            else:
                search_params['q'] = 'private:false'

        return search_params

    # implements IPackageController
    def after_search(self, search_results, search_params):
        '''
            Extensions will receive the search results, as well as the search
            parameters, and should return a modified (or not) object with the
            same structure:

                {'count': '', 'results': '', 'facets': ''}

            Note that count and facets may need to be adjusted if the extension
            changed the results for some reason.

            search_params will include an `extras` dictionary with all values
            from fields starting with `ext_`, so extensions can receive user
            input from specific fields.

        '''
        if 'owner_org' in search_params['q']:
            datasets = search_results['results']
            for dataset in datasets:
                if dataset['private'] and not (meta_helper.is_user_owns_package(dataset['id'], p.toolkit.c.user) or
                                               self.has_user_group_or_org_admin_role(dataset['owner_org'],
                                                                                     p.toolkit.c.user)):

                    # update dataset count for dataset groups
                    for group in dataset['groups']:
                        for item in search_results['search_facets']['groups']['items']:
                            if item.get('name') == group['name']:
                                item['count'] -= 1
                                break

                    # update dataset count for the organization
                    search_results['search_facets']['organization']['items'][0]['count'] -= 1
                    # update dataset counts by license
                    for item in search_results['search_facets']['license_id']['items']:
                        if item.get('name') == dataset['license_id']:
                            item['count'] -= 1
                            break

                    # update dataset count by each tag
                    for tag in dataset['tags']:
                        for item in search_results['search_facets']['tags']['items']:
                            if item.get('name') == tag['name']:
                                item['count'] -= 1
                                break

                    # update resource format counts
                    updated_formats = []
                    for resource in dataset['resources']:
                        res_format = resource['format']
                        if res_format in updated_formats:
                            continue
                        search_results['facets']['res_format'][res_format] -= 1
                        for item in search_results['search_facets']['res_format']['items']:
                            if item.get('name') == res_format:
                                item['count'] -= 1
                                updated_formats.append(res_format)
                                break

                    # remove the dataset since the user does not have access to it
                    search_results['results'].remove(dataset)

            # remove any facet items that has a count of zero or less
            facet_items_to_delete = {}
            facets = search_results['search_facets']
            for key, value in facets.iteritems():
                for facet_item in value['items']:
                    if facet_item['count'] <= 0:
                        if key not in facet_items_to_delete:
                            facet_items_to_delete[key] = {'items': []}
                            facet_items_to_delete[key]['items'].append(facet_item)
                        else:
                            facet_items_to_delete[key]['items'].append(facet_item)

            for facet_key in facet_items_to_delete:
                for item_to_delete in facet_items_to_delete[facet_key]['items']:
                    search_results['search_facets'][facet_key]['items'].remove(item_to_delete)

        return search_results

    # implements IPackageController
    def after_show(self, context, pkg_dict):
        '''
            Extensions will receive the validated data dict after the package
            is ready for display (Note that the read method will return a
            package domain object, which may not include all fields).
        '''
        # We are cheating the system here by putting dummy data for the resources
        # so that we can create dataset without resources. Then in our own local pkg_update()
        # we are deleting this dummy data
        if pkg_dict['state'] == 'draft' or pkg_dict['state'] == 'draft-complete':
            if len(pkg_dict['resources']) == 0:
                pkg_dict['resources'] = [{'dummy_resource': '****'}]


def user_create_local(context, data_dict):   
        log.debug('my very own user_create() called')
        user_obj = core_user_create(context, data_dict)

        data_dict = {
            'id': 'iutah',
            'username': user_obj['name'],
            'role': 'editor'
        }

        context['ignore_auth'] = True
        # 'default' is CKAN' default sysadmin account username that can be used for adding a user to an organization
        context['user'] = 'default'
        p.toolkit.get_action('organization_member_create')(context, data_dict)
        return user_obj


def pkg_update(context, data_dict):
    log.debug('my very own package_update() called')

    # turning context 'validate' key on/off to allow schema changes to work with existing dataset
    context['validate'] = False
    origpkg = p.toolkit.get_action('package_show')(context, data_dict)
    context['validate'] = True

    # this is needed when adding a resource to an existing dataset
    if context.get('save', None) is None:
        for extra in origpkg['extras']:
            if data_dict.get(extra['key'], None) is None:
                data_dict[extra['key']] = extra['value']

    #get name of the author to use in citation
    author = origpkg.get('author', None)
    # get the name of the submitter to use in citation if author is not available
    sub_name = None
    sub_email = None
    submitter_dict = [extra for extra in origpkg['extras'] if extra['key'] == 'sub_name' or extra['key'] == 'sub_email']
    for extra in submitter_dict:
        if extra['key'] == 'sub_name':
            sub_name = extra['value']
        if extra['key'] == 'sub_email':
            sub_email = extra['value']

    if not sub_name:
        context['return_minimal'] = True
        # turning context 'validate' key on/off to allow schema changes to work with existing dataset
        context['validate'] = False
        user = p.toolkit.get_action('user_show')(context, {'id': context['user']})
        context['validate'] = True
        data_dict['sub_name'] = user['fullname']
        data_dict['sub_email'] = user['email']
    else:
        data_dict['sub_name'] = sub_name
        data_dict['sub_email'] = sub_email

    # TODO: may be we do not need the original CKAN author information
    if not author:
        data_dict['author'] = data_dict['sub_name']
        data_dict['author_email'] = data_dict['sub_email']


    data_dict['version'] = u'1.0'
    data_dict['license_id'] = u'cc-by'

    dateval = origpkg['metadata_created']
    year = dateval.split("-")[0]

    if origpkg['state'] != 'active':
        if data_dict.get('author', None):
            data_dict['citation'] = createcitation(context, data_dict, year)
        else:
            data_dict['citation'] = u''
    else:
        data_dict['citation'] = createcitation(context, data_dict, year)
        context['validate'] = False

    # This was added to allow creation metadata only dataset (dataset without resources)
    # Here we are deleting our dummy resource if it exists
    if origpkg['state'] == 'draft' or origpkg['state'] == 'draft-complete':
        if data_dict.get('resources', None):
            if len(data_dict['resources']) > 0:
                dummy_resource = data_dict['resources'][0]
                if dummy_resource.get('dummy_resource', None):
                    del data_dict['resources'][0]
        elif origpkg.get('resources', None):
            if len(origpkg['resources']) > 0:
                dummy_resource = origpkg['resources'][0]
                if dummy_resource.get('dummy_resource', None):
                    del origpkg['resources'][0]

    iutahorg = p.toolkit.get_action('organization_show')(context, {'id': 'iutah'})

    if not data_dict.get('owner_org', None):
        data_dict['owner_org'] = origpkg['owner_org']
        data_dict['private'] = origpkg['private']
    else:
        if data_dict['owner_org'] == iutahorg['id']:
            data_dict['private'] = origpkg['private']

    # remove if there any deleted repeatable elements from the data_dict
    _remove_deleted_repeatable_elements(data_dict, 'creators')
    _remove_deleted_repeatable_elements(data_dict, 'contributors')
    _remove_deleted_repeatable_elements(data_dict, 'variables')

    # add tag names to the tag_string element if 'tag_string' is missing from the data_dict
    # needed to make the entry of one tag (keyword) as required
    if not 'tag_string' in data_dict.keys():
        tags = ','.join(tag['name'] for tag in data_dict['tags'])
        data_dict['tag_string'] = tags

    return package_update(context, data_dict)


def show_user(context, data_dict):
    # this function solves the missing value error
    # when dataset schema is changed and we have old datasets
    # that were created prior to the schema change

    if not context.get('save', None):
        context['validate'] = False

    return user_show(context, data_dict)


def show_package(context, data_dict):
    # this function solves the missing value error
    # when dataset schema is changed and we have old datasets
    # that were created prior to the schema change
    if context.get('for_view', None) or context.get('for_edit', None) or context.get('pending', None) or \
            context.get('allow_partial_update', None):
        context['validate'] = False

    if context.get('resource', None):
        model = context['model']
        pkg = model.Package.get(data_dict['id'])
        data_dict = model_dictize.package_dictize(pkg, context)
        if check_if_dataset_using_older_schema(data_dict['extras']):
            context['validate'] = False

    return package_show(context, data_dict)


def check_if_dataset_using_older_schema(dataset_extras):
    # get the list of custom schema elements and check that against the dataset_extras
    if len(dataset_extras) == 0:
        return False

    common_metadata = [x['id'] for x in required_metadata + expanded_metadata]
    # only take into account the required repeatable elements
    repeatable_elements = ['creators', 'variables']
    extra_keys = [extra['key'] for extra in dataset_extras]
    extra_repeat_keys = [extra['key'] for extra in dataset_extras if len(extra['key'].split(':')) == 3]
    extra_repeat_keys_first_parts = [key.split(':')[0] for key in extra_repeat_keys]
    for custom_element in common_metadata:
        if custom_element not in extra_keys:
            return True
    for repeat_element in repeatable_elements:
        if repeat_element not in extra_repeat_keys_first_parts:
            return True

    return False


def createcitation(context, data_dict, year):
    
    url = h.url_for(controller='package', action='read', id=data_dict['name'], qualified=True)
    # turning context 'validate' key on/off to allow schema changes to work with existing dataset
    context['validate'] = False

    creators = data_dict.get('creators', None)
    citation_authors = ''
    if creators:
        for creator in creators:
            if creator['delete'] == '1':
                continue

            # check first if the creator is a group and if so no need need to split the name
            if 'is_a_group' in creator:
                if creator['is_a_group'] == '1':
                    citation_authors += creator['name'] + ", "
            else:
                name_parts = creator['name'].split(" ")
                if len(name_parts) > 1:     # this is when the name contains first name and last name
                    citation_authors += "{last_name}, {first_initial}.".format(last_name=name_parts[-1],
                                                                               first_initial=name_parts[0][0]) \
                                        + ", "
                elif len(name_parts) > 0:   # if only one name is provided use that as the last name
                    citation_authors += "{last_name}.".format(last_name=name_parts[-1]) + ", "

    # get rid of the last comma followed by a space (last 2 chars)
    citation_authors = citation_authors[:-2]
    version = 0       
    try:
        version = data_dict['version']
    except:
        version = 0
        
    citation = '{creator} ({year}), {title}, {version}, iUTAH Modeling & Data Federation, ' \
               '{url}'.format(creator=citation_authors, year=year, title=data_dict['title'], version=version, url=url)

    context['validate'] = True
    return citation


def pkg_create(context, data_dict):
    log.debug('my very own package_create() called') 

    # 'return_minimal' will only get the user information and not any dataset associated with the user
    # without return_minimal' the context object will change and point to some other dataset
    # which will get overwritten
    context['return_minimal'] = True
    user = p.toolkit.get_action('user_show')(context, {'id': context['user']})
    data_dict['sub_name'] = user['fullname']
    data_dict['sub_email'] = user['email']
    data_dict['creator_organization'] = ''
    data_dict['creator_address'] = ''
    data_dict['creator_phone'] = ''
    data_dict['version'] = u'1.0'
    data_dict['license_id'] = u'cc-by'
    data_dict['citation'] = u''

    #if organization is iutah
    iutahorg = p.toolkit.get_action('organization_show')(context, {'id': 'iutah'})

    if data_dict['owner_org'] == iutahorg['id']:
        data_dict['private'] = True

    # remove if there any deleted repeatable elements from the data_dict
    _remove_deleted_repeatable_elements(data_dict, 'creators')
    _remove_deleted_repeatable_elements(data_dict, 'contributors')
    _remove_deleted_repeatable_elements(data_dict, 'variables')

    p.toolkit.check_access('package_create',context, data_dict)
    pkg = package_create(context, data_dict)
    return pkg


def set_default_creator(data_dict, sub_name, sub_email):
    if len(data_dict['custom_meta']['creators']) == 0:
        creator = {'name': sub_name, 'email': sub_email, 'phone': '', 'address': '', 'organization': '',
                   'delete': '0', 'is_a_group': '0'}
        data_dict['custom_meta']['creators'].append(creator)


def _remove_deleted_repeatable_elements(data_dict, element_name):
    if element_name in data_dict:
        deleted_contributors = [c for c in data_dict[element_name] if c['delete'] == '1']
        for contributor in deleted_contributors:
            data_dict[element_name].remove(contributor)