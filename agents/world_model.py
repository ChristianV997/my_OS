import numpy as np

class WorldModel:

    def __init__(self):
        self.w6=None; self.w12=None; self.w24=None

    def featurize(self, action):
        return np.array([float(v) for v in action.values()])

    def _fit(self,X,y):
        try: return np.linalg.lstsq(X,y,rcond=None)[0]
        except: return None

    def train(self, event_log):
        rows=event_log.rows
        if len(rows)<20: return
        X=[]; y6=[]; y12=[]; y24=[]
        for r in rows:
            a={"variant": r.get("variant",0)}
            X.append(self.featurize(a))
            y6.append(r.get("roas_6h", r.get("roas",0)))
            y12.append(r.get("roas_12h", r.get("roas",0)))
            y24.append(r.get("roas_24h", r.get("roas",0)))
        X=np.array(X)
        self.w6=self._fit(X,np.array(y6))
        self.w12=self._fit(X,np.array(y12))
        self.w24=self._fit(X,np.array(y24))

    def _pred(self,w,x):
        if w is None: return 1.0
        try: return float(np.dot(x,w))
        except: return 1.0

    def predict(self, action):
        x=self.featurize(action)
        return {"roas_6h":self._pred(self.w6,x),"roas_12h":self._pred(self.w12,x),"roas_24h":self._pred(self.w24,x)}

world_model=WorldModel()
