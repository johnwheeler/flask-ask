"""
Stream cache functions
"""


def push_stream(stream_cache, user_id, stream):
    """
    Push a stream onto the stream stack in cache.
    user_id: id of user, used as key in cache
    stream: stream object to push onto stack
    returns: True on successful update,
     False if failed to update, and None if invalid
    input was given (e.g. stream is None)
    """
    stack = stream_cache.get(user_id)
    if stack is None:
        stack = []
    if stream:
        stack.append(stream)
        return stream_cache.set(user_id, stack)
    return None


def pop_stream(stream_cache, user_id):
    stack = stream_cache.get(user_id)
    if stack is None:
        return None

    token = stack.pop()

    if len(stack) == 0:
        stream_cache.delete(user_id)
    else:
        stream_cache.set(user_id, stack)

    return token


def set_stream(stream_cache, user_id, stream):
    if stream:
        return stream_cache.set(user_id, [stream])


def top_stream(stream_cache, user_id):
    stack = stream_cache.get(user_id)
    if stack is None:
        return None
    return stack.pop()
