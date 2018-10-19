Flask-Ask provides a dictionary of “slots” for its applications.  The keys of the slots dictionary are the slot names as they are referenced in the Intent; the values are built with Slot objects defined in core.py.

For example, slots for the AddItemIntent might be {'product_daily_brew': \<SlotData\>} with SlotData.value (what the user said) = "cup of coffee" and SlotData.enties=[\<Entities\>].  Entity objects are for slot value entity resolutions.  The entity .name is the slot value name (e.g. 'Smoothies', 'frozen_lemonade', 'twenty_ounce') while the entity .id is the slot value id (e.g. 'Beverages_3', 'PRODUCT_74', 'mc_size_3')

Slot: https://developer.amazon.com/docs/custom-skills/request-types-reference.html#slot-object

Entity: https://developer.amazon.com/docs/custom-skills/request-types-reference.html#resolutions-object
