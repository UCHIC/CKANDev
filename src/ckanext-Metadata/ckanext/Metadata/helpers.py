__author__ = 'pabitra'
import ckan.lib.base as base
import ckan.plugins as p
import logging
from sqlalchemy import *
from ckan import model

tk = p.toolkit
_ = tk._  # translator function
log = logging.getLogger('ckan.logic')


def table(name):
    return Table(name, model.meta.metadata, autoload=True)


def is_user_owns_package(package_id, username):
    """
    check if a given user identified by the username owns a given dataset/package
    identified by package_id. Returns True if owns otherwise False

    @param package_id: id of the dataset/package
    @param username: user name of the user
    @return: True or False
    """

    package_obj = base.model.Package.get(package_id)
    package_role_table = table('package_role')
    user_object_role_table = table('user_object_role')

    # setting the field context == 'Package' and field role=='admin' of the
    # user_object_role table gives us the id of the user who owns (uploaded) a given resource
    sql = select([user_object_role_table.c.user_id], from_obj=[package_role_table.join(user_object_role_table)]).\
        where(package_role_table.c.package_id == package_obj.id).\
        where(user_object_role_table.c.context == 'Package').where(user_object_role_table.c.role == 'admin')

    # the following query execution gives us a list containing one user id (since there
    # can be only one owner for a given dataset) for the user
    # who have ownership for the provided package_id
    query_result = base.model.Session.execute(sql).first()
    if query_result:
        package_owner_id = query_result[0]
        resource_owner = base.model.User.get(unicode(package_owner_id))
        if resource_owner:
            if resource_owner.name == username:
                return True
            else:
                return False
    else:
        return False