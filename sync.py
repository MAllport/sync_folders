import argparse
# While one could use sys.argv to process arguments directly, the "argparse" 
# package makes it exceedingly easy to provide short and long options, as well
# as document the proper usage of those arguments through --help
from glob import glob
# The "glob" package makes UNIX-style path patterns available in Python,
# simplifying the path logic significantly
from datetime import datetime # Timestamps
from typing import TextIO # Type hints for file objects
from os import path, makedirs, rmdir, remove # Path and create/removal helpers
import shutil # Copying operations
from time import sleep # Sleep operations
from pathlib import Path # Path object

# Function to return prematurely if any of the provided folders do not exist
def valid_folder(folder_name: str):
    if not path.exists(folder_name):
        raise argparse.ArgumentTypeError(
            "{0} does not exist".format(folder_name))
    return folder_name

def synchronize_folders(original_path: str, synchronized_path: str) -> dict:
    actions = {}
    # Action dictionary to log information of which folders and files
    # have been created/removed/copied
    original_content = glob(f"{original_path}/**", recursive= True)[1:]
    synchronized_content = glob(f"{synchronized_path}/**", recursive= True)[1:]
    # Could include hidden folders, but the parameter was only added in
    # Python 3.11 and so is omitted.
    # I'm also not sure what is the proper use to handle symlinks,
    # but I'm assuming this is outside the scope of the task
    
    # glob returns a list like so: 
    # ["*original_path*/file1.txt","*original_path*/folder1/file2.txt"].
    
    rel_original_content = [path.relpath(p, original_path) for p
                            in original_content]
    rel_synchronized_content = [path.relpath(p, synchronized_path) for p
                            in synchronized_content]
    # Returns a list like so:
    # [file1.txt, folder1/file2.txt]
    set_original_content = set(rel_original_content)
    set_synchronized_content = set(rel_synchronized_content)
    actions['created'] = list(set_original_content - set_synchronized_content)
    actions['removed'] = list(set_synchronized_content - set_original_content)
    actions['copied']  = list(set_original_content.intersection
                              (set_synchronized_content))
    # This set logic relies on the fact that every file path is unique -
    # an assumption that has to be true for any copy/delete/create
    # operation to be functioning in the first place
    
    for file_path in sorted(actions['created'], 
                            key= lambda fp: len(Path(fp).parents)):
        # Here we are sorting based on the depth of the folder or file
        # Sorting makes the order of operations much easier seeing as
        # you always create folders before creating the files within them
        
        src_path = f"{original_path}/{file_path}"
        dst_path = f"{synchronized_path}/{file_path}"
        if path.isdir(src_path):
            makedirs(dst_path)
        else:
            shutil.copy2(src_path, dst_path)
        
        # copy2() retains metadata such as when the file was created
        # and modified. Seeing as we are to maintain a full identical copy
        # I'm assuming this is in order
        
    for file_path in (fp for fp in actions['copied'] 
                      if len(Path(fp).parents) == 1):
        # Because copytree() copies the entire tree of the given directory,
        # we are only interested in the files and folders that are in the root
        # directory. We therefore filter the file path list before we continue
        
        src_path = f"{original_path}/{file_path}"
        dst_path = f"{synchronized_path}/{file_path}"
        if path.isdir(src_path):
            shutil.copytree(src_path, dst_path, dirs_exist_ok = True)
        else:
            shutil.copy2(src_path, dst_path)
    
    # Above I made the choice to overwrite any existing folders and files
    # The advantages to this approach is that it's reduntantly foolproof -
    # it easily retains any metadata and any changes to the content inside
    # the files, which might be harder to track.
    # However, if files are large, the synchronization interval is low,
    # or resources are constrained, the redundancy might be very costly.
    # Another approach in that case could be to track whether the file or folder
    # has been modified, and only follow through with the overwrite if it has
    
    for file_path in sorted(actions['removed'], reverse = True,
                        key= lambda fp: len(Path(fp).parents)):
        # Reversing the order of the sort because we want to delete a file
        # before deleting the folder containing it
        
        src_path = f"{original_path}/{file_path}"
        dst_path = f"{synchronized_path}/{file_path}"
        
        if not path.isdir(dst_path):
            remove(dst_path)
        else:
            rmdir(dst_path)
    
    return actions
        
# Helper function to reduce excessive nesting for readability
def log_and_print(actions: dict[str, list], f: TextIO):
    for action_key in actions.keys():
        for action_path in actions[action_key]:
            now = datetime.now().replace(microsecond=0)
            action_string = (f"{now} {action_key.capitalize()}"
                        f" file with file path {action_path}")
            f.write(f"{action_string}\n")
            print(action_string)
            

def log_and_print_actions(actions: dict, log_path: str):
    with open(f"{log_path}/sync_log.txt", 'w') as f:
        pass
    # Above I'm choosing to delete the contents of the old log file before 
    # writing to it. 
    # Another solution could be to instead preserve old log files
    # and create new ones like sync_log_1.txt, sync_log_2.txt etc. on
    # different runs of the program with the same log folder
    with open(f"{log_path}/sync_log.txt", 'a') as f:
        log_and_print(actions, f)
        

def synchronization_loop(original_path: str, synchronized_path: str,
                         log_path: str, 
                         synchronization_interval_seconds: int):
    while True:
        now = datetime.now().replace(microsecond=0)
        print(f"{now} Started synchronization from {original_path} to " 
              f"{synchronized_path} with a synchronization interval of "
              f"{synchronization_interval_seconds} seconds")
        actions = synchronize_folders(original_path, synchronized_path)
        log_and_print_actions(actions, log_path)
        print(f"{now} Synchronization complete")
        sleep(synchronization_interval_seconds)
        # Note that there are several downsides to using "sleep":
        # 1) sleep is blocking, so any SIGINT or SIGTERM sent will wait
        # until the sleep is finished before exiting the program
        # 2) Any SIGINT or SIGTERM sent while the program is copying files
        # might lead to data corruption in the synchronized folder
        
        # A proper solution could be to use some kind of threading,
        # catch any signals, and then do some sort of data integrity check
        # based on the contents of the original folder before exiting gracefully
        
        # I'm assuming this is outside of the scope of the task, and assuming
        # the "perfect" use of the program

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=
                                     "One-way synchronization of a folder")
    parser.add_argument("-o", "--original_path", dest="original_path",
                        required=True, type=valid_folder,
                        help="The file path of the folder to be synchronized")
    parser.add_argument("-s", "--synchronized_path", 
                        dest="synchronized_path",
                        required=True, type=valid_folder,
                        help="The file path of the copied synced folder")
    parser.add_argument("-l", "--log_path", 
                        dest="log_path",
                        required=True, type=valid_folder,
                        help="The file path of the log folder")
    parser.add_argument("-i", "--synchronization_interval_seconds", 
                        dest="synchronization_interval_seconds",
                        required=True, type=int,
                        help="The synchronization interval in seconds")
    args = parser.parse_args()
    synchronization_loop(args.original_path, 
                         args.synchronized_path,
                         args.log_path, 
                         args.synchronization_interval_seconds)