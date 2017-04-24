"""
Stream cache functions
"""


def push_stream(cache, user_id, stream):
    """
    Push a stream onto the stream stack in cache.

    :param cache: werkzeug BasicCache-like object
    :param user_id: id of user, used as key in cache
    :param stream: stream object to push onto stack

    :return: True on successful update,
             False if failed to update,
             None if invalid input was given
    """
    stack = cache.get(user_id)
    if stack is None:
        stack = []
    if stream:
        stack.append(stream)
        return cache.set(user_id, stack)
    return None


def pop_stream(cache, user_id):
    """
    Pop an item off the stack in the cache. If stack
    is empty after pop, it deletes the stack.

    :param cache: werkzeug BasicCache-like object
    :param user_id: id of user, used as key in cache

    :return: top item from stack, otherwise None
    """
    stack = cache.get(user_id)
    if stack is None:
        return None

    result = stack.pop()

    if len(stack) == 0:
        cache.delete(user_id)
    else:
        cache.set(user_id, stack)

    return result


def set_stream(cache, user_id, stream):
    """
    Overwrite stack in the cache.

    :param cache: werkzeug BasicCache-liek object
    :param user_id: id of user, used as key in cache
    :param stream: value to initialize new stack with

    :return: None
    """
    if stream:
        return cache.set(user_id, [stream])


def top_stream(cache, user_id):
    """
    Peek at the top of the stack in the cache.

    :param cache: werkzeug BasicCache-like object
    :param user_id: id of user, used as key in cache

    :return: top item in user's cached stack, otherwise None
    """
    if not user_id:
        return None
    
    stack = cache.get(user_id)
    if stack is None:
        return None
    return stack.pop()
