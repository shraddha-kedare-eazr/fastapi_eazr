# Function to get top 5 contacts for a given user_id and call logs
def get_top_5_contacts(call_logs):
    contacts_count = {}
    for log in call_logs:
        number = log.get('Number')
        if number in contacts_count:
            contacts_count[number] += 1
        else:
            contacts_count[number] = 1
    
    sorted_contacts = sorted(contacts_count.items(), key=lambda x: x[1], reverse=True)
    return sorted_contacts[:5]

# Function to find neardear contacts for a given user_id and call logs
def find_neardear_contacts(call_logs, threshold=3):
    neardear_contacts = []
    if call_logs:
        contacts_count = {}
        for log in call_logs:
            number = log.get('Number')
            if number in contacts_count:
                contacts_count[number] += 1
            else:
                contacts_count[number] = 1
        
        for contact, count in contacts_count.items():
            if count >= threshold:
                neardear_contacts.append((contact, count))
    
    return neardear_contacts
