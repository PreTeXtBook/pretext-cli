####
# Wrappers for functions supplied by mathbook/pretext.  
# Using this file, we have all the calls to the external pretext/pretext script in one place so we can update them if there is a remote change.
# Each function here is a slightly tweaked name of a function from pretext/pretext

from .static.pretext import pretext as ptxcore

def set_verbosity(verbosity):
    ptxcore.set_verbosity(verbosity)

def latex_image_conversion(xml_source, pub_file, stringparams, xmlid_root, data_dir, dest_dir, outformat):
    ptxcore.latex_image_conversion(xml_source, pub_file, stringparams, xmlid_root, data_dir, dest_dir, outformat)


def sage_conversion(xml_source, pub_file, stringparams, xmlid_root, dest_dir, outformat):
    ptxcore.sage_conversion(xml_source, pub_file, stringparams, xmlid_root, dest_dir, outformat)


#Not functional yet:
# def all_images(xml_source, pub_file, stringparams, xmlid_root, data_dir, dest_dir, outformat):
#     ptxcore.all_images(xml_source, pub_file, stringparams, xmlid_root)

def webwork_to_xml(xml_source, pub_file, stringparams,                   abort_early, server_params, dest_dir):
    ptxcore.webwork_to_xml(xml_source, pub_file, stringparams, abort_early, server_params, dest_dir)
