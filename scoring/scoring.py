import sys
print(sys.path)


def get_location_score(zipcode):
    default_zipcodes = open('sample/default_pincode.txt', 'r').read().split(',')
    alert_zipcodes = open('sample/alert_pincodes.txt', 'r').read().split(',')
    location_score = 0
    if zipcode in default_zipcodes or zipcode in alert_zipcodes:
        location_score = 0
    else:
        location_score = 25
    return location_score

def get_finapp_score(number_of_financial_apps):
   
    if 1 < number_of_financial_apps <= 5:
        return 15
    elif 5 < number_of_financial_apps <= 10:
        return 10
    elif 10 < number_of_financial_apps <= 15:
        return 5
    elif  number_of_financial_apps >15:
        return 0
    else:
        return 25
