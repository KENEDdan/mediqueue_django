from django import template

register = template.Library()

@register.filter
def get_item(dictionary, key):
    """Get a form field by name: form|get_item:'field_name'"""
    return dictionary[key]