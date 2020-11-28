#
#   Basic caching single level dict
#   @cache_element(cache='my_cache', target_kwarg='targ_kwarg')
#   def foo(self, target_kwarg):
#
def cache_element(cache, target_kwarg):
    def _cache_element(func):
        def wrapper(self, *args, **kwargs):
            cache_ = getattr(self, cache)
            # if key not in cache create entry
            key = kwargs[target_kwarg]
            if key not in cache_:
                cache_[key] = func(self, *args, **kwargs)
            # return cached element
            return (cache_[key])
        return (wrapper)
    return (_cache_element)

#
#   Handle actual caching (is_valid is important for efficiency in my implementation)
#   @handle_ui_element_cache(cache='class_attr_cache_name', target_element='key_to_element')
#   def foo(self, *args):
#
def handle_ui_element_cache(cache, target_element):
    def _handle_ui_element_cache(func):
        def wrapper(self, *args):
            cache_ = getattr(self, cache)
            # if target_element not in cache create entry
            if target_element not in cache_:
                cache_[target_element] = dict(
                        element=None,
                        is_valid=False
                    )
            # if target_element is new or invalid call func to get fresh element
            # .. and save to cache
            if not cache_[target_element]['is_valid']:
                cache_[target_element]['element'] = func(self, *args)
                cache_[target_element]['is_valid'] = True
            # return cached element
            return (cache_[target_element]['element'])
        return (wrapper)
    return (_handle_ui_element_cache)

#
#   Invalidate single cache entry
#   @invalidate_ui_element_cache(cache='class_attr_cache_name', target_element='key_to_element')
#   def foo(self, *args, **kwargs):
#
def invalidate_ui_element_cache(cache, target_element):
    def _invalidate_ui_element_cache(func):
        def wrapper(self, *args, **kwargs):
            cache_ = getattr(self, cache)
            # if target_element not in cache create entry
            if target_element not in cache_:
                cache_[target_element] = dict(
                        element=None,
                        is_valid=False
                    )
            cache_[target_element]['is_valid'] = False
            return (func(self, *args, **kwargs))
        return (wrapper)
    return (_invalidate_ui_element_cache)

#
#   Invalidate entire cache
#   @invalidate_cache(cache='class_attr_cache_name')
#   def foo(self, *args, **kwargs):
#
def invalidate_cache(cache):
    def _invalidate_cache(func):
        def wrapper(self, *args, **kwargs):
            cache_ = getattr(self, cache)
            for key, elem in cache_.items():
                elem['is_valid'] = False

            return (func(self, *args, **kwargs))
        return (wrapper)
    return (_invalidate_cache)