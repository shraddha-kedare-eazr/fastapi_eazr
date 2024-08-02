def read_apps_from_file(file_path):
    with open(file_path, 'r') as file: 
        apps_list = file.read().splitlines()
    return apps_list

def match_apps(installed_apps, categorized_apps):
    matched_apps = []
    for app in installed_apps:
        if app in categorized_apps:
            matched_apps.append(app)
    return matched_apps
