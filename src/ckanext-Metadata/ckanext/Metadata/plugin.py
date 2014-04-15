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
                     {'id': 'observed_variables', 'validators': [v.String(max=100)]},
                     # used for testing schema change {'id': 'test_element', 'validators': [v.String(max=100)]},

                     #TODO should this unique_id be validated against any other unique IDs for this agency?
                     #{'id':'unique_id', 'validators': [v.String(max=100)]}
)

#optional metadata
expanded_metadata = (
                        {'id': 'spatial', 'validators': [v.String(max=500)]},
                        {'id': 'temporal', 'validators': [v.String(max=300)]},
                        {'id': 'purpose', 'validators': [v.String(max=100)]},
                        {'id': 'collection', 'validators': [v.String(max=1000)]},
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

                        {'id': 'update_frequency', 'validators': [v.Regex(r'^([Dd]aily)|([Hh]ourly)|([Ww]eekly)|([yY]early)|([oO]ther)$')]},

                        {'id': 'study_area', 'validators': [v.String(max=100)]},
                        {'id': 'units', 'validators': [v.String(max=100)]},
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
    deleteIndex = []

    for data_key, data_value in new_data.iteritems():
        #If this is a deleted record then add it to the deleted list to be removed from data later.
        if 'delete' in data_key and data_value == '1':
            deleteIndex.append(data_key[1])

    deleted = []

    for data_key, data_value in new_data.iteritems():
        if len(data_key) > 1 and data_key[1] in deleteIndex:
            deleted.append(data_key)

    for item in deleted:
        del new_data[item]

    # update the index in the keys for the creators since some of the creators may have been deleted by the user
    # so that we can have the indexes in the keys in a sequence starting at 0
    creator_index_to_adjust = 0
    last_used_deleted_index = 0
    keys_to_delete = []
    new_data_to_add = []

    if len(deleteIndex) > 0:
        for data_key, data_value in new_data.iteritems():
            if len(data_key) > 1:
                if data_key[1] > min(deleteIndex) and data_key[1] != 0:
                    if creator_index_to_adjust != 0 and creator_index_to_adjust != data_key[1]:
                        del deleteIndex[last_used_deleted_index]
                    if creator_index_to_adjust == data_key[1]:
                        new_data_key = (data_key[0], min(deleteIndex), data_key[2])
                        new_data_to_add.append({new_data_key: new_data[data_key]})
                        #new_data[new_data_key] = new_data[data_key]
                        keys_to_delete.append(data_key)
                    else:
                        creator_index_to_adjust = data_key[1]
                        last_used_deleted_index = min(deleteIndex)
                        new_data_key = (data_key[0], last_used_deleted_index, data_key[2])
                        new_data_to_add.append({new_data_key: new_data[data_key]})
                        #new_data[new_data_key] = new_data[data_key]
                        keys_to_delete.append(data_key)

        for key in keys_to_delete:
            del new_data[key]

        for dict in new_data_to_add:
            for key, value in dict.iteritems():
                new_data[key] = value
                break

    #Add data extracted from extras to the data dictionary
    for data_key, data_value in new_data.iteritems():
        data[data_key] = data_value


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

        # creators:1:name # for creator#2
        # creators:1:email
        # creators:1:phone
        # creators:1:address
        # creators:1:organization

        # In the generated new new_dict we want the set of creator data as follows:
        # new_dict['custom_meta']['creators'] = [
        #                           {'name': name1-value, 'email': email1-value, 'phone': phone1-value, 'address': address1-value, 'organization': org1-value}
        #                           {'name': name2-value, 'email': email2-value, 'phone': phone2-value, 'address': address2-value, 'organization': org2-value}
        #                           { .......}
        #                        ]
        try:
            new_dict['custom_meta']
        except KeyError:
            new_dict['custom_meta'] = {}

        new_dict['custom_meta']['creators'] = []

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
                    # check if the key matches the creators repeatable metadata element
                    data_key_parts = extra['key'].split(':')
                    if data_key_parts[0] == 'creators' and len(data_key_parts) == 3:
                        creator_dataset_index = int(data_key_parts[1])
                        if creator_dataset_index == len(new_dict['custom_meta']['creators']):
                            creator = {data_key_parts[2]: extra['value']}
                            new_dict['custom_meta']['creators'].append(creator)
                        else:
                            new_dict['custom_meta']['creators'][creator_dataset_index][data_key_parts[2]] = extra['value']
                    else:
                        reduced_extras.append(extra)

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

            for key in keys_to_remove:
                del new_dict[key]

            # add the default creator if no creator exists at this point
            set_default_creator(new_dict, sub_name, sub_email)

        # remove any creators marked as deleted from the dict
        creators = [c for c in new_dict['custom_meta']['creators'] if c['delete'] != '1']
        new_dict['custom_meta']['creators'] = creators

        return new_dict

    @classmethod
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

    # template helper function
    @classmethod
    def get_research_focus(cls):
        '''        log.debug('get_research_focus() called')
            Jinja2 template helper function, gets the vocabulary for research focus
        '''
        user = p.toolkit.get_action('get_site_user')({'ignore_auth': True}, {})
        context = {'user': user['name']}

        vocab = None
        try:
            data = {'id': 'research_focus'}  # we can use the id or name for id param
            vocab = p.toolkit.get_action('vocabulary_show')(context, data)
        except:
            log.debug("vocabulary_show failed, meaning the vocabulary for research focus doesn't exist")
            vocab = cls.__create_vocabulary('research_focus', u'RFA1', u'RFA2', u'RFA3', u'other', u'CI', u'EOD')

        research_focus = [x['display_name'] for x in vocab['tags']]
        log.debug("vocab tags: %s" % research_focus)

        return research_focus

    # template helper function
    @classmethod
    def get_update_frequency(cls):
        '''
        log.debug('get_update_frequency() called')
            Jinja2 template helper function, gets the vocabulary for update_frequency
        '''
        user = p.toolkit.get_action('get_site_user')({'ignore_auth': True}, {})
        context = {'user': user['name']}

        vocab = None
        try:
            data = {'id': 'update_frequency'}  # we can use the id or name for id param
            vocab = p.toolkit.get_action('vocabulary_show')(context, data)
        except:
            log.debug("vocabulary_show failed, meaning the vocabulary for update_frequency doesn't exist")
            vocab = cls.__create_vocabulary('update_frequency', u'hourly', u'daily', u'weekly', u'yearly', u'monthly',
                                            u'real time', u'other')

        update_frequency = [x['display_name'] for x in vocab['tags']]
        log.debug("vocab tags: %s" % update_frequency)

        return update_frequency

    # template helper function
    @classmethod
    def get_study_area(cls):
        '''        log.debug('get_study_area() called')
            Jinja2 template helper function, gets the vocabulary for access levels
        '''
        user = p.toolkit.get_action('get_site_user')({'ignore_auth': True}, {})
        context = {'user': user['name']}
 
        vocab = None
        try:
            data = {'id': 'study_area'}  # we can use the id or name for id param
            vocab = p.toolkit.get_action('vocabulary_show')(context, data)
        except:
            log.debug("vocabulary_show failed, meaning the vocabulary for study area doesn't exist")
            vocab = cls.__create_vocabulary(u'study_area', u'other', u'WRMA-Wasatch Range Metropolitan Area',
                                            u'Logan River Watershed', u'Red Butte Creek Watershed',
                                            u'Provo River Watershed', u'Multiple Watersheds')
 
        study_area = [x['display_name'] for x in vocab['tags']]
        log.debug("vocab tags: %s" % study_area)
 
        return study_area

    # template helper function
    @classmethod
    def get_types(cls):
        '''        log.debug('type() called')
            Jinja2 template helper function, gets the vocabulary for type
        '''
        user = p.toolkit.get_action('get_site_user')({'ignore_auth': True}, {})
        context = {'user': user['name']}
 
        vocab = None
        try:
            data = {'id': 'type'}   # we can use the id or name for id param
            vocab = p.toolkit.get_action('vocabulary_show')(context, data)
        except:
            log.debug("vocabulary_show failed, meaning the vocabulary for type doesn't exist")
            vocab = cls.__create_vocabulary(u'type', u'dataset', u'model', u'collection', u'other')

        types = [x['display_name'] for x in vocab['tags']]
        log.debug("vocab tags: %s" % types)
 
        return types

    # template helper function
    @classmethod
    def get_status(cls):
        '''        log.debug('get_study_area() called')
            Jinja2 template helper function, gets the vocabulary for status
        '''
        user = p.toolkit.get_action('get_site_user')({'ignore_auth': True}, {})
        context = {'user': user['name']}
 
        vocab = None
        try:
            data = {'id': 'status'}  # we can use the id or name for id param
            vocab = p.toolkit.get_action('vocabulary_show')(context, data)
        except:
            log.debug("vocabulary_show failed, meaning the vocabulary for status doesn't exist")
            vocab = cls.__create_vocabulary(u'status', u'complete', u'ongoing', u'planned', u'unknown')
 
        status = [x['display_name'] for x in vocab['tags']]
        log.debug("vocab tags: %s" % status)
 
        return status
    
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

        for update in schema_updates_for_create:
            schema.update(update)

        schema.update({'creators': creator_schema()}) # needed for repeatable elements
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

        schema.update({'creators': [convert_from_extras, ignore_missing]}) # needed for repeatable elements
        return schema

    #Method below allows functions and other methods to be called from the Jinja template using the h variable
    def get_helpers(self):
        return {'get_research_focus': self.get_research_focus, 
                'required_metadata': required_metadata,
                'load_data_into_dict':  self.load_data_into_dict,
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
            ds_count = 0
            datasets = search_results['results']
            for dataset in datasets:
                if dataset['private'] and not (meta_helper.is_user_owns_package(dataset['id'], p.toolkit.c.user) or
                                               self.has_user_group_or_org_admin_role(dataset['owner_org'],
                                                                                     p.toolkit.c.user)):
                    ds_count += 1

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

            search_results['count'] -= ds_count

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
    author = data_dict.get('author', None)

    # get the name of the submitter to use in citation if author is not available
    sub_name = origpkg.get('sub_name', None)
    sub_email = origpkg.get('sub_email', '')
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
            data_dict['citation'] = createcitation(context, data_dict, year)  # createcitation(context, data_dict, subname=author)
        else:
            data_dict['citation'] = u''
    else:
        data_dict['citation'] = createcitation(context, data_dict, year)  # createcitation(context, data_dict, subname=author)
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

    return package_show(context, data_dict)


def createcitation(context, data_dict, year):    # (context, data_dict, subname=None, year=None)
    
    url = h.url_for(controller='package', action='read', id=data_dict['name'], qualified=True)
    # turning context 'validate' key on/off to allow schema changes to work with existing dataset
    context['validate'] = False

    creators = data_dict.get('creators', None)
    citation_authors = ''
    if creators:
        for creator in creators:
            if creator['delete'] == '1':
                continue

            name_parts = creator['name'].split(" ")
            if len(name_parts) > 1: # this is when the name contains first name and last name
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
                       
    p.toolkit.check_access('package_create',context, data_dict)
    pkg = package_create(context, data_dict)
    return pkg


def set_default_creator(data_dict, sub_name, sub_email):
    if len(data_dict['custom_meta']['creators']) == 0:
        creator = {'name': sub_name, 'email': sub_email, 'phone': '', 'address': '', 'organization': '', 'delete': ''}
        data_dict['custom_meta']['creators'].append(creator)