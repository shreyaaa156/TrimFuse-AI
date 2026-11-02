import streamlit as st
import pandas as pd
import numpy as np
from pathlib import Path
from sklearn.ensemble import HistGradientBoostingRegressor, RandomForestRegressor, ExtraTreesRegressor
from sklearn.metrics import mean_absolute_error, mean_squared_error, r2_score
from sklearn.model_selection import GroupShuffleSplit

st.set_page_config(page_title="TrimFuse AI | Semiconductor Test Intelligence", page_icon="⚙️", layout="wide")
ROOT=Path(__file__).parent
DATA=ROOT/"data"
PCM=["pcm_vth_n_mV","pcm_vth_p_mV","pcm_rs_ohm_sq","pcm_tox_A","pcm_mobility_rel"]
POS=["x_mm","y_mm","radius_mm"]
@st.cache_data
def load(name): return pd.read_csv(DATA/name)
@st.cache_resource
def train_mcu():
    df=load('mcu_trim_fuse.csv'); df=df[df.derivative=='MCU-A'].copy()
    feats={"Bandgap":["bg_untrim_V"]+PCM+POS,"HSI":["hsi_untrim_MHz"]+PCM+POS,"LDO":["ldo_untrim_V"]+PCM+POS}
    # Hold out complete wafers; deterministic split.
    gss=GroupShuffleSplit(n_splits=1,test_size=.25,random_state=42)
    tr_i,te_i=next(gss.split(df,groups=df.wafer_id)); tr,te=df.iloc[tr_i],df.iloc[te_i]
    models={}; metrics=[]
    for name,(target,cols,bits) in {"Bandgap":("bg_trim_code_opt",feats['Bandgap'],6),"HSI":("hsi_trim_code_opt",feats['HSI'],7),"LDO":("ldo_trim_code_opt",feats['LDO'],5)}.items():
        candidates={"HistGradientBoosting":HistGradientBoostingRegressor(max_iter=300,learning_rate=.08,random_state=0),"RandomForest":RandomForestRegressor(n_estimators=250,min_samples_leaf=2,n_jobs=-1,random_state=0),"ExtraTrees":ExtraTreesRegressor(n_estimators=250,min_samples_leaf=2,n_jobs=-1,random_state=0)}
        best=None; best_mae=1e9
        for mname,m in candidates.items():
            m.fit(tr[cols],tr[target]); pred=np.clip(np.rint(m.predict(te[cols])),0,2**bits-1)
            mae=mean_absolute_error(te[target],pred)
            if mae<best_mae: best,best_mae=(mname,m),mae
        mname,model=best; pred=np.clip(np.rint(model.predict(te[cols])),0,2**bits-1); y=te[target].to_numpy(); err=np.abs(pred-y)
        models[name]=(model,cols,bits)
        metrics.append({"Target":name,"Selected model":mname,"MAE (codes)":round(mean_absolute_error(y,pred),3),"RMSE (codes)":round(mean_squared_error(y,pred)**.5,3),"Exact match":f"{(err==0).mean():.1%}","Within ±1":f"{(err<=1).mean():.1%}","Test dies":len(te)})
    return models,pd.DataFrame(metrics),df
models,metrics,mcu=train_mcu()
st.title("⚙️ TrimFuse AI")
st.caption("AI-assisted trim prediction, derivative support and fuse-map verification | Synthetic assessment dataset")
with st.sidebar:
    st.header("Navigation")
    page=st.radio("Choose module",["Overview","MCU Trim Predictor","Fuse Map Safety Audit","PMIC & Sensor Insights","SoC & Memory Insights"])
    st.info("Safety: predictions are advisory. Always measure and verify on tester before any OTP fuse programming.")
if page=="Overview":
    st.subheader("Assessment workspace")
    files={"MCU dies":("mcu_trim_fuse.csv",8420),"PMIC dies":("pmic_trim_otp.csv",11060),"Sensor dies":("sensor_calibration.csv",11060),"SoC dies":("soc_binning_harvesting.csv",6160),"Fuse audit records":("mcu_fuse_map_audit.csv",1500),"Memory repair cases":("memory_repair_bitmaps.csv",3000)}
    cols=st.columns(3)
    for i,(label,(fn,n)) in enumerate(files.items()): cols[i%3].metric(label,f"{len(load(fn)):,}")
    st.markdown("### Implemented workflow")
    st.markdown("1. Inspect process-monitor and pre-trim measurements.\n2. Predict candidate trim codes with wafer-grouped model validation.\n3. Verify predicted outputs with a tester measurement.\n4. Validate fuse words against derivative-specific rules.\n5. Fall back to conventional search whenever confidence or verification is insufficient.")
    st.warning("All supplied datasets are synthetic. This prototype is for evaluation and must not program real fuses.")
elif page=="MCU Trim Predictor":
    st.subheader("Single-die MCU trim recommendation")
    a=mcu[mcu.derivative=='MCU-A']
    idx=st.selectbox("Choose a sample die",a.index.tolist(),format_func=lambda x:a.loc[x,'die_id'])
    r=a.loc[idx]
    c1,c2,c3=st.columns(3)
    fields=[("Bandgap", "bg_untrim_V","V"),("HSI","hsi_untrim_MHz","MHz"),("LDO","ldo_untrim_V","V")]
    for col,(name,field,unit) in zip([c1,c2,c3],fields):
        val=col.number_input(f"{name} untrimmed ({unit})",value=float(r[field]),format="%.5f",key=field)
    row=r.copy()
    for _,field,_ in fields: row[field]=st.session_state[field]
    if st.button("Predict candidate trim codes",type="primary"):
        results=[]
        for name,(model,features,bits) in models.items():
            pred=int(np.clip(np.rint(model.predict(pd.DataFrame([row[features].to_dict()]))[0]),0,2**bits-1))
            results.append((name,pred,bits))
        cc=st.columns(3)
        for col,(name,pred,bits) in zip(cc,results): col.metric(f"{name} trim code",pred, f"{bits}-bit range: 0–{2**bits-1}")
        st.success("Candidate codes generated. Apply only after tester verification and limit checks.")
        st.caption("The model was trained on MCU-A and held-out wafers. Predictions for other derivatives require derivative-specific validation/fine-tuning.")
    st.markdown("### Held-out wafer performance")
    st.dataframe(metrics,use_container_width=True,hide_index=True)
elif page=="Fuse Map Safety Audit":
    st.subheader("Derivative-aware fuse-map validation")
    audit=load('mcu_fuse_map_audit.csv'); schema=load('mcu_fuse_schema.csv'); st.write("Upload a CSV containing `derivative` and `fuse_map_hex`, or inspect the supplied audit dataset.")
    up=st.file_uploader("Upload fuse audit CSV",type="csv")
    d=pd.read_csv(up) if up else audit
    required={'derivative','fuse_map_hex'}
    if not required.issubset(d.columns): st.error("CSV must contain derivative and fuse_map_hex columns.")
    else:
        expected={"MCU-A":(1,0xFF,0),"MCU-B":(0,0x3F,0),"MCU-C":(2,0xFF,1)}
        def check(row):
            if row.derivative not in expected:return "UNKNOWN_DERIVATIVE"
            try:w=int(str(row.fuse_map_hex),16)
            except:return "INVALID_HEX"
            fl,pe,rdp=expected[row.derivative]
            problems=[]
            if ((w>>30)&3)!=fl:problems.append('FLASH_SIZE')
            if ((w>>32)&255)!=pe:problems.append('PERIPHERAL_MASK')
            if not ((w>>41)&1):problems.append('DEBUG_LOCK')
            if ((w>>42)&1)!=rdp:problems.append('READ_PROTECT')
            if (w>>43)!=0:problems.append('RESERVED_BITS')
            return ';'.join(problems) if problems else 'PASS'
        d=d.copy();d['audit_result']=d.apply(check,axis=1);d['safe_to_proceed']=d.audit_result.eq('PASS')
        x,y,z=st.columns(3);x.metric("Records",len(d));y.metric("Passed",int(d.safe_to_proceed.sum()));z.metric("Flagged",int((~d.safe_to_proceed).sum()))
        st.dataframe(d,use_container_width=True,hide_index=True)
        st.download_button("Download audit results",d.to_csv(index=False),"fuse_map_audit_results.csv","text/csv")
        st.error("A PASS from this software audit is not authorization to blow OTP fuses. Independent hardware and security sign-off remains mandatory.")
elif page=="PMIC & Sensor Insights":
    st.subheader("PMIC coupled-rail and sensor-calibration datasets")
    pm=load('pmic_trim_otp.csv'); sn=load('sensor_calibration.csv')
    a,b=st.columns(2);a.metric("PMIC characterization rows",f"{len(pm):,}");b.metric("Sensor calibration rows",f"{len(sn):,}")
    st.markdown("**PMIC:** supplied baseline predicts four rail trim codes from reference measurements and PCM/process features, without directly measuring each rail.")
    st.dataframe(pm.groupby('derivative').size().rename('dies').reset_index(),hide_index=True)
    st.markdown("**Sensor:** supplied baseline trains on fully characterized 3-temperature dies and predicts temperature coefficients for reduced-insertion calibration.")
    st.dataframe(sn.groupby('characterized_3temp').size().rename('dies').reset_index(),hide_index=True)
    st.info("Use wafer-grouped validation and tester measurements before deploying either workflow.")
elif page=="SoC & Memory Insights":
    st.subheader("SoC performance prediction and memory repair")
    soc=load('soc_binning_harvesting.csv');mem=load('memory_repair_bitmaps.csv')
    core=[f'core{i}_fmax_GHz' for i in range(8)];soc['slowest_core_fmax_GHz']=soc[core].min(axis=1)
    a,b,c=st.columns(3);a.metric("SoC dies",f"{len(soc):,}");b.metric("Mean slowest-core Fmax",f"{soc.slowest_core_fmax_GHz.mean():.3f} GHz");c.metric("Memory cases",f"{len(mem):,}")
    st.markdown("**SKU mix in supplied rule-based labels**")
    st.bar_chart(soc.sku_rule_based.value_counts())
    st.markdown("**Greedy versus exact memory repair**")
    st.metric("Additional arrays repaired by exact allocation",int((mem.optimal_repairable & ~mem.greedy_repairable).sum()))
    st.dataframe(mem[['greedy_repairable','optimal_repairable']].mean().rename('repairable_rate').reset_index(),hide_index=True)
