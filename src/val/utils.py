import os



def load_prompt(self, prompt_fn):
    #__file__是Python中内置的变量,它表示当前文件的文件名
    new_fn = os.path.join(os.path.dirname(__file__), prompt_fn)

    try:
        with open(new_fn, 'r') as f:
            return f.read().strip()
    except:
        print('error loading prompt from filename %s' % (new_fn,))
        return None

