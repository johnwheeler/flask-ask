#!/usr/bin/env 
import os
import inspect
from flask import json

from ask_audio import ask



def generate_schema(skill):
    """Generates Intent Model Schema json file from the skills intent functions.

    If your skill uses custom slot types, please view IntentSchema.json
    and enter the custom slot type filename as the value for slot type.

    This process will overwrite any exsiting content in speechAssets/IntentSchema.

    Arguments:
        skill {Ask object} -- Ask app initialized with flask app.
                              Import from the script it was created in.
    """

    skill.init_app(skill.app)
    output = os.path.join(skill.app.root_path, 'speechAssets/IntentSchema.json')

    if os.path.isfile(output):
        print("""It appears you have already have an IntentSchema.json file.
        Running this command will overwrite any existing schema.\n""")

        confirm = input("Do you wish to continue? [y/n]")
        if confirm != 'n':
            quit

    schema = {'intents': []}

    for intent_name in skill._intent_view_funcs:
        new_intent = {'intent': intent_name}
        slot_names = get_slot_names(skill, intent_name)

        if slot_names:
            new_intent['slots'] = []
        for slot_name in slot_names:
            slot_type = get_slot_type(skill, intent_name, slot_name)
            slot_name = get_slot_from_param(skill, intent_name, slot_name)
            new_intent['slots'].append({'name': slot_name, 'type': slot_type})

        schema['intents'].append(new_intent)

    with open(output, 'w') as f:
        json.dump(schema, f, indent=2)


def custom_slot_types(skill):
    custom_dir = os.path.join(skill.app.root_path, 'speechAssets/CustomSlotTypes')
    if not os.path.isdir(custom_dir):
        return []
        
    custom_types = []
    for f in os.listdir(custom_dir):
        # print(type(f))
        if '.' in f:  # custom slot is an extension of an amazon slot
            slot_type = f
        else:
            slot_type = f.split('OF_')[1]
    custom_types.append(slot_type)
    return custom_types


def get_slot_names(skill, intent_name):
    view_func = skill._intent_view_funcs[intent_name]
    slot_names = inspect.getargspec(view_func).args
    return slot_names


def get_slot_type(skill, intent_name, slot_name=None):

    intent_conversion = skill._intent_converts[intent_name]
    slot_conversion = intent_conversion.get(slot_name)

    if slot_conversion == int:
        return 'AMAZON.NUMBER'

    # # TODO find way to identify custom skill file from the slot/parameter name
    # # custom slot file name will often be the plural of the type.
    # # user will often need to enter these custom types manually
    custom_look_up = 'LIST_OF_{}'.format(slot_name.upper())
    if custom_look_up in custom_slot_types(skill):
        return custom_look_up

    # provides the amazon intent type if flask-ask handles
    # the slot_conversion with a string constant
    handled_data_types = {
        'date': 'AMAZON.DATE',
        'time': 'AMAZON.TIME',
        'timedelta': 'AMAZON.DURATION'
    }

    slot_type = handled_data_types.get(slot_name.lower(), None)
    if not slot_type:
        return '**ENTER SLOT TYPE HERE**'
    else:
        return slot_type


def get_slot_from_param(skill, intent_name, slot_name=None):
    mapping = skill._intent_mappings[intent_name]

    mapped_slot = mapping.get(slot_name, slot_name)
    return mapped_slot

if __name__ == '__main__':
    generate_schema(ask)
