# dict->list conversion
def dict_to_list(dict_input, clientside):
    list_output = []
    if clientside:
        keys = ["action", "username", "passhash", "user2", "sender", "recipient", 
                "message", "sent_message", "n_messages", "message_id"]
    else:
        keys = ["result", "users", "n_undelivered", "messages", "message_id", 
                "sender", "sent_message"]
    for key in keys:
        if key in dict_input:
            list_output.append(dict_input[key])
        else:
            list_output.append(None)
    return list_output

# list->dict conversion
def list_to_dict_server(list_input, clientside):
    dict_output = {}
    if clientside:
        keys = ["result", "users", "n_undelivered", "messages", "message_id",
                "sender", "sent_message"]
    else:
        keys = ["action", "username", "passhash", "user2", "sender", "recipient",
                "message", "sent_message", "n_messages", "message_id"]
    for i in range(len(keys)):
        if list_input[i] is not None:
            dict_output[keys[i]] = list_input[i]
    return dict_output

# list->string conversion
def list_to_string(list_input):
    sanitized_list = [str(x).replace(",", "\\,") for x in list_input]
    return ",".join(sanitized_list)

# string->list conversion
def string_to_list(string_input):
    split_list = string_input.split(",")
    desanitized_list = [x.replace("\\,", ",") for x in split_list]
    return desanitized_list
