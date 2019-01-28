import time

def lru(func):
        def wrapper(*args, **kwargs):
            # print("------------------inside lru decorator------------------")
            cache_list = func(*args, **kwargs)
            if len(cache_list)<=5:
                # print(cache_list)
                return cache_list
            else:
                # for i in range(len(cache_list)-5):
                cache_list.pop(list(cache_list.keys())[0])
                # print(cache_list)
                return cache_list
        return wrapper
