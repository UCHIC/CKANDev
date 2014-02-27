# {% set dataset_is_draft = data.get('state', 'draft').startswith('draft') or data.get('state', 'none') ==  'none' %}
#   {% set dataset_has_organization = data.owner_org or data.group_id %}

from logging import getLogger
import ckan.plugins as p
import formencode.validators as v
import copy
from ckan.logic.action.create import user_create as core_user_create, package_create
from ckan.logic.action.update import package_update
import ckan.lib.helpers as h

log = getLogger(__name__)

#excluded title, description, tags and last update as they're part of the default ckan dataset metadata
required_metadata = (
                     {'id': 'language', 'validators': [v.String(max=100)]},
                     
                     {'id': 'data_type', 'validators': [v.String(max=100)]},
                     {'id': 'access_information', 'validators': [v.String(max=500)]},#use_constraints
                     {'id': 'intended_use', 'validators': [v.String(max=100)]},
                     {'id': 'status', 'validators': [v.String(max=100)]},
                     {'id': 'observed_variables', 'validators': [v.String(max=100)]},

                     #TODO should this unique_id be validated against any other unique IDs for this agency?
                     #{'id':'unique_id', 'validators': [v.String(max=100)]}
)

#optional metadata
expanded_metadata = (
                        {'id': 'spatial', 'validators': [v.String(max=500)]},
                        {'id': 'temporal', 'validators': [v.String(max=300)]},
                        {'id': 'purpose', 'validators': [v.String(max=100)]},
                        {'id': 'collection', 'validators': [v.String(max=1000)]},

                        {'id': 'sub_name', 'validators': [v.String(max=100)]},
                        {'id': 'sub_email', 'validators': [v.String(max=100)]},
                        {'id': 'creator_organization', 'validators': [v.String(max=100)]},
                        {'id': 'creator_address', 'validators': [v.String(max=100)]},
                        {'id': 'creator_phone', 'validators': [v.String(max=50)]},
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

        #new_dict = data_dict.copy()
        new_dict = copy.deepcopy(data_dict)
        common_metadata = [x['id'] for x in required_metadata+expanded_metadata]

        try:
            new_dict['custom_meta']
        except KeyError:
            new_dict['custom_meta'] = {}

        reduced_extras = []

        try:
            for extra in new_dict['extras']:

                if extra['key'] in common_metadata:
                    new_dict['custom_meta'][extra['key']]=extra['value']
                else:
                    reduced_extras.append(extra)

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
            for key,value in new_dict.iteritems():
                #TODO remove debug
                log.debug('checking key: {0}'.format(key))
                if key in common_metadata:
                    #TODO remove debug
                    log.debug('adding key: {0}'.format(key))
                    new_dict['custom_meta'][key]=value
                    keys_to_remove.append(key)

            for key in keys_to_remove:
                del new_dict[key]

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

    #See ckan.plugins.interfaces.IDatasetForm
    def _modify_package_schema(self, schema):
        #log.debug("_modify_package_schema called")

        for update in schema_updates_for_create:
            schema.update(update)

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
        #log.debug('show_package_schema')
        schema = super(MetadataPlugin, self).show_package_schema()

        # Don't show vocab tags mixed in with normal 'free' tags
        # (e.g. on dataset pages, or on the search page)
        schema['tags']['__extras'].append(p.toolkit.get_converter('free_tags_only'))

        for update in schema_updates_for_show:
            schema.update(update)

        return schema

    #Method below allows functions and other methods to be called from the Jinja template using the h variable
    def get_helpers(self):
        return {'get_research_focus': self.get_research_focus, 
                'required_metadata': required_metadata,
                'load_data_into_dict':  self.load_data_into_dict,
                'study_area': self.get_study_area,
                'get_status':self.get_status,
                'get_types':self.get_types,
                'update_frequency': self.get_update_frequency}

    #See ckan.plugins.interfaces.IActions    
    def get_actions(self):
        log.debug('get_actions() called') 
        return {
                 'package_create': pkg_create,
                 'package_update': pkg_update,
                 'user_create': user_create_local
        }


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

    origpkg = p.toolkit.get_action('package_show')(context, data_dict)
    sub_name = origpkg.get('sub_name', None)

    context['return_minimal'] = True
    user = p.toolkit.get_action('user_show')(context, {'id': context['user']})

    data_dict['sub_name'] = user['fullname']
    data_dict['sub_email'] = user['email']

    data_dict['version'] = u'1.0'
    data_dict['license_id'] = u'cc-by'

    if origpkg['state'] != 'active':
        data_dict['citation'] = u''
        if not data_dict.get('author', None):
            data_dict['author'] = u''
            data_dict['author_email'] = u''
            data_dict['creator_organization'] = u''
            data_dict['creator_address'] = u''
            data_dict['creator_phone'] = u''
        else:
            data_dict['citation'] = createcitation(context, data_dict, subname=sub_name)
    else:
        data_dict['citation'] = createcitation(context, data_dict, subname=sub_name)

    iutahorg = p.toolkit.get_action('organization_show')(context, {'id': 'iutah'})

    if not data_dict.get('owner_org', None):
        data_dict['owner_org'] = origpkg['owner_org']
        data_dict['private'] = origpkg['private']
    else:
        if data_dict['owner_org'] == iutahorg['id']:
            data_dict['private'] = origpkg['private']

    return package_update(context, data_dict)


def createcitation(context, data_dict, subname=None, year=None):
    
    url = h.url_for(controller='package', action='read', id=data_dict['name'], qualified=True)
    origpkg = p.toolkit.get_action('package_show')(context, data_dict)
    
    name = subname
    try:
        if len(data_dict['author']) > 0:
            name = data_dict['author']
    except:
        name = subname           
    
    creator = "{last}, {fi}.".format(last=name.split(" ")[-1], fi=name.split(" ")[0][0])
    version = 0       
    try:
        version = data_dict['version']
    except:
        version = 0 
    
    if not year:        
        dateval = p.toolkit.get_action('package_show')(context, data_dict)['metadata_created']
        year = dateval.split("-")[0]
        
    citation = '{creator} ({year}), {title}, {version}, iUTAH Modeling & Data Federation, ' \
               '{url}'.format(creator=creator, year=year, title=data_dict['title'], version=version, url=url)
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

