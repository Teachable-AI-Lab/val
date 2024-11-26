import numpy as np
import warnings
from abc import ABCMeta
from abc import abstractmethod
from cre import Flattener, Vectorizer, FactSet

# from cre.utils import PrintElapse
# from .registers import register_when
# from ....shared import ElapseLogger

# NOTE: Seems like maybe Task instances include their
#   match? So we'll keep  as the match for now
#   it seems to be a frozen=True dataclass which beats
#   using __str__()

# NOTE: Doesn't need to be like 
class SkillApp:
    def __init__(self, state, method, match):
        self.state = state
        self.method = method

        
        self.match = tuple(match)

    def __hash__(self):
        return hash((
            str(self.method),
            str(self.state),
            hash(self.match)
        ))

    def __eq__(self, other):
        return (
            str(self.method) == str(other.method) and 
            str(self.state) == str(other.state) and 
            self.match == other.match
        ) 



class BaseCondLearner(metaclass=ABCMeta):
    def __init__(self, skill,**kwargs):

        self.skill = skill
        self.check_sanity = kwargs.get('sanity_check', True)

        # Note this line makes it possible to call 
        super(BaseCondLearner, self).__init__(skill, **kwargs)

    def sanity_check_ifit(self, state, skill_app, reward):
        # SANITY CHECK: Classifier Inconsistencies 
        if(self.check_sanity and reward is not None):
            prediction = self.predict(state, skill_app.match)
            if(reward != prediction):
                print(self)
                raise Exception(f"(Sanity Check Error): Condition-learning mechanism"+
                 f" for skill {self.skill}"
                 f" .predict() produces different outcome ({prediction:.2f}) than reward given in" +
                 f" .ifit() ({reward:.2f}). This most likely indicates 1) that the agent" +
                 " requires additional feature prior knowledge to distinguish between two"+
                 " now indistinguishable situations. Alternatively 2) this may indicate an error in the "+
                 " when-learning mechanism or in the preparation of the state representation.")

    def __init_subclass__(cls, **kwargs):
        super().__init_subclass__(**kwargs)
        
        # Inject sanity checks after ifit
        ifit = cls.ifit
        def ifit_w_sanity_check(self, state, skill_app, reward):

            ifit(self, state, skill_app, reward)
            if(self.check_sanity):
                self.sanity_check_ifit(state, skill_app, reward)
        setattr(cls, 'ifit', ifit_w_sanity_check)


    def ifit(self, state, skill_app, reward):
        """
        
        :param state: 
        """
        raise NotImplemented()

    def fit(self, states, skill_apps, reward):
        """
        
        """
        raise NotImplemented()

    def score(self, state, skill_app):
        """
        
        """
        raise NotImplemented()

    def as_conditions(self):
        """
        
        """
        raise NotImplemented()

    def predict(self, state, match):
        """
        
        """
        raise NotImplemented()

    def get_info(self, **kwargs):
        return {}

# --------------------------------------------
# : RefittableMixin

class RefittableMixin():
    '''A mixin which implements add_example() and remove_example().
        self.examples maps skill_apps to tuples of (index, reward)
     '''
    def __init__(self, skill,**kwargs):
        self.examples = {}

    def transform(self, state, match):
        '''Should take in a state and skill_app and return '''
        raise NotImplemented()

    def insert_transformed(self, transformed_state, skill_app, reward, index):
        raise NotImplemented()

    def remove_index(self):
        raise NotImplemented()        

    def _assert_skill_app_from_state(self, state, skill_app):
        assert state.get('__uid__') == skill_app.state_uid, (
            f"Provided state {state.get('__uid__')} is not associated with skill app: {skill_app}"
        )

    def add_example(self, state, skill_app, reward):
        ''' Adds a new training example. Applies transform() and insert_transformed() 
            from the child class. Checks to see if the example is new or a repeat and 
            returns the new index or possibly old index for the example and the add 
            attempt changed the set of training examples.
        ''' 
        # self._assert_skill_app_from_state(state, skill_app)
        did_change = False
        index, old_reward = self.examples.get(skill_app,(-1,0))
        # if(index != -1): 
        #     print("REPLACING FEEDBACK", skill_app, old_reward, "->", reward, "@ index", index)

        new_index = index
        if(reward is None and index != -1):
            self.remove_example(state, skill_app)
            return -1
        elif(reward is not None):
            new_index = len(self.examples) if index == -1 else index

            # NOTE: temping to only re-insert on reward changes, but meta-features can make it helpful
            #  to retrain if possible new feautres. 
            self.examples[skill_app] = (new_index, reward)
            transformed_state = self.transform(state, skill_app.match)
            
            # print(transformed_state, skill_app, reward, new_index)
            # print("INSERT", transformed_state)

            self.insert_transformed(transformed_state, skill_app, reward, new_index)
                
        return new_index

    def remove_example(self, state, skill_app):
        ''' Attempt to remove a skill_app instance from the training set.
            Shifts the set of indicies and calls rebase_examples() from the
            child class.
        '''
        
        # raise ValueError("REMOVE EXAMPLE")
        # self._assert_skill_app_from_state(state, skill_app)
        did_change = False
        index, old_reward = self.examples.get(skill_app,(-1,0))
        if(index != -1):
            # print("REMOVE EXAMPLE", skill_app)
            for skill_app, (ind, reward) in self.examples.items():
                if(ind > index):
                    self.examples[skill_app] = (ind-1, reward)
            del self.examples[skill_app]
            did_change = True
            self.remove_index(index)
            # self.rebase_examples()

        return index, did_change



class VectorTransformMixin(RefittableMixin):
    def __init__(self, skill, encode_relative=False, one_hot=False,
                add_exist_stubs=True, rel_enc_min_sources=None,
                # starting_state_format='flat_featurized',
                extra_features=[],
                 **kwargs):
        super().__init__(skill,**kwargs)
        # self.starting_state_format = 'flat_featurized'
        self.encode_relative = encode_relative
        self.extra_features = extra_features
        self.one_hot = one_hot
        self.add_exist_stubs = add_exist_stubs
        self.rel_enc_min_sources = rel_enc_min_sources

        # Initialize Flattener, Vectorizer
        from cre import Flattener, Vectorizer
        self.flattener = Flattener()
        self.vectorizer = Vectorizer()

        # Recovers original keys and values...
        def inv_mapper(key_ind, _val):
            fact = self.vectorizer.invert(key_ind, _val)
            fact = (*fact,)
            key = fact[:-1]
            val = fact[-1]
            is_neg = _val==0
            return is_neg, key, val
        self.inv_mapper = inv_mapper

        # Initialize or retrive relative_encoder
        if(encode_relative):
            # TODO: Write this
            from cre import RelativeEncoder
            self.relative_encoder = RelativeEncoder()

        self.X_nom = np.empty((0,0), dtype=np.int64)
        self.Y = np.empty(0, dtype=np.int64)

    def transform(self, state, match):
        factset_state = FactSet.from_py(state)
        featurized_state = self.flattener.apply(factset_state)

        # TODO implement this        
        for extra_feature in self.extra_features:
            featurized_state = extra_feature(self, state, featurized_state, match)


        # TODO: implement this
        if(self.encode_relative):
            self.relative_encoder.set_in_memset(wm)

            sources = match
            if(self.rel_enc_min_sources is not None):
                sources = sources[:self.rel_enc_min_sources]
                _vars = _vars[:self.rel_enc_min_sources]

            featurized_state = self.relative_encoder.encode_relative_to(
                featurized_state, sources, _vars)

        nominal, continuous = self.vectorizer.apply(featurized_state)
        return nominal, continuous


    def insert_transformed(self, transformed_state, skill_app, reward, index):
        nominal, continuous = transformed_state

        n, m = self.X_nom.shape
        new_shape = (max(n, index+1), max(m, len(nominal)))
        
        if(new_shape != self.X_nom.shape):
            # print("NEW SHAPE", new_shape, n, index+1, m, len(nominal))
            # Copy old data into new matrix
            new_X_nom = np.zeros(new_shape, dtype=np.int64)
            new_Y = np.zeros(new_shape[0], dtype=np.int64)
            new_X_nom[:n, :m] = self.X_nom
            new_Y[:n] = self.Y

            # Copy old data into new training matrix
            self.X_nom = new_X_nom
            self.Y = new_Y

        self.X_nom[index] = nominal
        self.Y[index] = reward
        # print("GGGG")
        # print(self.X_nom,  self.Y)

    def remove_index(self, index):
        self.X_nom = np.concatenate([self.X_nom[:index], self.X_nom[index+1:]])
        self.Y = np.concatenate([self.Y[:index], self.Y[index+1:]])



class BasicSTAND(BaseCondLearner, VectorTransformMixin):
    def __init__(self, skill, **kwargs):
        super().__init__(skill, **kwargs)
        # Note: Most STAND tends to work best without one-hot by default
        kwargs['one_hot'] = kwargs.get('one_hot', False)
        BaseCondLearner.__init__(self, skill,**kwargs)
        VectorTransformMixin.__init__(self, skill, **kwargs)

    def ifit(self, state, skill_app, reward):
        self.add_example(state, skill_app, reward) # Insert into X_nom, Y
        # print("AFTER")
        # print(self.X_nom)
        if(len(self.X_nom) == 0): return

        # with PrintElapse(f"{type(self).__name__} fit:"):
        self.classifier.fit(self.X_nom, None, self.Y) # Re-fit

    def fit(self, skill_app_reward_pairs):
        cover = set()
        old_apps = set(self.examples.keys())
        for skill_app, reward in skill_app_reward_pairs:
            state = skill_app.state
            cover.add(skill_app)
            self.add_example(state, skill_app, reward) # Insert into X_nom, Y

        not_cover = old_apps.difference(cover)
        for skill_app in not_cover:
            state = skill_app.state
            state.remove_example(state, skill_app)

        self.classifier.fit(self.X_nom, None, self.Y) # Re-fit

    def remove(self, state, skill_app):
        self.remove_example(state, skill_app) # Remove from X_nom, Y
        if(len(self.X_nom) == 0): return
        self.classifier.fit(self.X_nom, None, self.Y) # Re-fit

    def predict(self, state, match):
        if(len(self.X_nom) == 0): return 1
        nominal, continuous = self.transform(state, match)
        X_nom_subset = nominal[:self.X_nom.shape[1]].reshape(1,-1)
        prediction = self.classifier.predict(X_nom_subset, None)[0]        
        return prediction

    def get_lit_priorities(self):
        '''A string representation of a tree usable for the purposes of debugging'''
        lps = self.classifier.op_tree_classifier.get_lit_priorities(self.inv_mapper)
        return lps

    def _lit_to_pyHTN(self, lit):
        is_neg, key, val = lit
        lit = (*key, val)
        if(is_neg):
            lit = ("not", lit)
        return lit


    def get_conds(self, literals="all", conjuncts="all"):
        opt_conjs = self.classifier.op_tree_classifier.get_conds(1, literals, conjuncts)
        return opt_conjs

    def get_pyHTN_conds(self, literals="all", conjuncts="all"):
        '''A string representation of a tree usable for the purposes of debugging'''
        opt_conjs = self.classifier.op_tree_classifier.get_conds(1, literals, conjuncts)

        py_opt_conjs = []
        for i, opt_conj in enumerate(opt_conjs):
            conj = []
            for j, opt_lits in enumerate(opt_conj):
                if(literals == "all"):
                    lit = []
                    for k, sp in enumerate(opt_lits):
                        lit.append(self._lit_to_pyHTN(sp))
                elif(literals == "random"):
                    sp = choice(list())
                    lit = self._lit_to_pyHTN(sp)
                conj.append(lit)
            py_opt_conjs.append(conj)

        return py_opt_conjs
        # from stand.tree_classifier import TTYPE_NODE

        # tree = self.classifier.op_tree_classifier.tree
        # nom_v_inv_maps = tree.data_stats.nom_v_inv_maps
        # inv_mapper = self.inv_mapper

        # lit_priorities = {}
        # N = None
        # for n_ind, node in enumerate(tree.nodes):
        #     ttype, index, splits, counts = node.ttype, node.index, node.split_data, node.counts
        #     sample_inds = node.sample_inds

        #     # The root is always first
        #     if(n_ind == 0):
        #         N = len(sample_inds)
        #     priority = len(sample_inds) / N

        #     op = node.op_enum
        #     if(ttype == TTYPE_NODE):
        #         for i, sd in enumerate(splits):
        #             if(not sd.is_continous): 
        #                 inv_map = nom_v_inv_maps[sd.split_ind]

        #                 # Recover the X vector indicies and values as provided before internal remapping
        #                 inp_key = sd.split_ind
        #                 inp_val = inv_map[sd.val]

        #                 # If inv_mapper was provided then use it to recover the true feature key
        #                 #   and value before the user's vectorization preprocessing.
        #                 if(inv_mapper):
        #                     inp_key, inp_val = inv_mapper(inp_key, inp_val)

        #                 # Convery `inp_key` Fact to tuple
        #                 key_tup = (*inp_key,)

        #                 curr_pr = lit_priorities.get(key_tup, 0.0)
        #                 if(priority > curr_pr):
        #                     lit_priorities[key_tup] = priority
        #             else:
        #                 thresh = np.int32(sd.val).view(np.float32) if op != OP_EQ else np.int32(sd.val)
        #                 instr = str_op(op)+str(thresh) if op != OP_ISNAN else str_op(op)

        #                 # TODO: Implement Continous Case
        #                 raise NotImplemented()
        #     else:
        #         # Ignore leaves
        #         pass

        # return [(pr,lit) for lit,pr in lit_priorities.items()]

    def __str__(self):
        return str(self.classifier)


class DecisionTree(BasicSTAND):
    def __init__(self, skill, impl="decision_tree",
                **kwargs):
        super().__init__(skill, **kwargs)
        from stand.tree_classifier import TreeClassifier
        self.classifier = TreeClassifier(impl, inv_mapper=self.inv_mapper)

# --------------------------------------------
# : STAND

# @register_when
class STAND(BasicSTAND):
    def __init__(self, skill, cert_kind="instance_certainty", **kwargs):
        super().__init__(skill, **kwargs)
        from stand.stand import STANDClassifier
        self.classifier = STANDClassifier(inv_mapper=self.inv_mapper, **kwargs)

        if(cert_kind == "instance_certainty"):
            # from stand.stand import instance_certainty
            self.prob_func = STANDClassifier.instance_certainty
        elif(cert_kind == "specific_only"):
            # from stand.stand import instance_certainty
            self.prob_func = STANDClassifier.predict_prob

class DecisionTree(BasicSTAND):
    def __init__(self, skill, impl="decision_tree",
                **kwargs):
        super().__init__(skill, **kwargs)
        from stand.tree_classifier import TreeClassifier
        self.classifier = TreeClassifier(impl, inv_mapper=self.inv_mapper)

