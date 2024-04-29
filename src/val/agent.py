from val.utils import load_prompt

class ValAgent:

    def __init__(self, websocket, openai_key : str):
        self.websocket = websocket
        self.openai_key = openai_key

        self.segment_prompt = load_prompt("prompts/chat_segmenter new.txt")


    def interpret(self, instruction,defs):
        actions=[]
        for seg in parser.segmentGPT(instruction):
            action=parser.nameGPT(seg)
             send({'message': action})
        #     if pred not in defs:
        #         pass
        #         #actions.append(newAction(seg,defs))
        #     else:
        #         emit({'message': (pred,args)})
        #         v=parser.verbalizeGPT((pred,args))
        #         emit({'message': v})
        #         yesno=parser.paraphraseGPT(v,seg)
        #         if yesno=='yes':
        #             emit({'message': yesno})
        #             actions.append((pred,args))
        #         else:
        #             pass
        #             #actions.append(newAction(seg,defs))
        return actions
