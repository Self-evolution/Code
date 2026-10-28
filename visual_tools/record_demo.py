"""Record a reproducible demo without altering the supplied research code.

Example, from the repository root after extracting Code.zip:
    python visual_tools/record_demo.py --project-root Code --output-dir demo_output

Uses the project's NumPy, pandas, and PyTorch requirements. A CUDA GPU is not
required for this demo. It loads checkpoints/td3_4auv.pt from the supplied project.
No checkpoint is trained or modified. Reusing an output directory replaces its
trace.csv and trace_metadata.json files.
"""
from pathlib import Path
import sys, json, hashlib, platform, time, argparse
from dataclasses import asdict
import numpy as np
import pandas as pd
import torch
parser=argparse.ArgumentParser(description="Record an illustrative CAMPE simulation trace from the supplied checkpoint.")
parser.add_argument('--project-root',type=Path,default=Path('.'),help='Extracted code directory containing campe/ and checkpoints/.')
parser.add_argument('--output-dir',type=Path,default=Path('demo_output'),help='Separate directory for CSV and metadata; original results are not changed.')
parser.add_argument('--seed',type=int,default=0)
parser.add_argument('--scenario',choices=['source','current','target_evasion','burst_loss','channel_shadow','localization','dynamics','thruster','gradual','sudden','joint','recurrent','mobile_shadow','relay_intercept','strong_current','direction_switch','long_burst_loss','random_target','deceptive_target','sensor_anomaly','severe_thruster','adversarial_mix','blackout_chase','recurrent_shift'],default='joint')
parser.add_argument('--method',choices=['source_only','domain_randomization','direct_finetune','stdw','ctta','campe'],default='campe')
parser.add_argument('--planner',choices=['fixed','fim','fim_mobility','dynamic_period','dual_plane','full_mpc'],default='full_mpc')
parser.add_argument('--device',default='cpu',help='cpu (default), cuda, or an explicit PyTorch device.')
args=parser.parse_args()
ROOT=args.project_root.resolve(); OUT=args.output_dir.resolve()
if not (ROOT/'campe'/'policy.py').is_file():
    parser.error('--project-root must contain campe/policy.py and checkpoints/.')
OUT.mkdir(parents=True,exist_ok=True)
sys.path.insert(0,str(ROOT))
from campe.config import SimConfig, DomainConfig
from campe.environment import PursuitEnv
from campe.policy import AdaptiveController
from campe.experiment import checkpoint_path, _initial_info, _domain_for, _capture_profiles

# Single-thread CPU execution is usually fastest for this small numerical workload.
torch.set_num_threads(1)
cfg=SimConfig()
seed=args.seed; scenario=args.scenario; planner=args.planner; method=args.method
env=PursuitEnv(cfg,seed=seed)
obs=env.reset(); info=_initial_info(env)
checkpoint=checkpoint_path(ROOT,'td3',cfg.n_auv)
controller=AdaptiveController(cfg,method,checkpoint,seed=seed,device=args.device)
rows=[]

def record(step,info,domain,previous_learning,planning_confidence):
    row={
        'step':step,'time_s':env.step_id*cfg.dt,
        'score':info['score'],'radius_error':info['radius_error'],'max_gap':info['max_gap'],
        'target_inside':info['target_inside'],'min_pair':info['min_pair'],'stable':info['stable'],
        'aoi':float(np.mean(env.aoi)),'per':float(np.mean(env.per_ema)),
        'risk':info['risk'],'control_ratio':env.control_ratio,'reserved_telemetry_ratio':1-env.control_ratio,
        'control_bytes_step':env.last_control_bytes_step if step>=0 else 0,
        'telemetry_bytes_step':env.learning_bytes-previous_learning,
        'control_bytes_cumulative':env.control_bytes,'telemetry_bytes_cumulative':env.learning_bytes,
        'drift':controller.drift_score,'model_drift':controller.model_drift_score,
        'communication_drift_component':.65*float(np.mean(env.per_ema))+.10*float(np.mean(env.aoi)),
        'update_weight':controller.update_weight,'learning_active':controller.learning_active,
        'adapter_norm':float(np.linalg.norm(controller.adapter)),
        'anchor_norm':float(np.linalg.norm(controller.anchor_adapter)),
        'kinematic_novelty':controller.kinematic_novelty_score,
        'planner_confidence_before_step':planning_confidence,
        'planner_fallback':float(env.full_mpc_fallback_active),
        'usv_distance':env.usv_distance,
        'target_x':env.target_pos[0],'target_y':env.target_pos[1],
        'usv_x':env.usv_pos[0],'usv_y':env.usv_pos[1],
        'usv_waypoint_x':env.usv_waypoint[0],'usv_waypoint_y':env.usv_waypoint[1],
        'domain_current_x':domain.current_x,'domain_current_y':domain.current_y,
        'domain_packet_loss':domain.packet_loss,
        'domain_thruster_health':domain.thruster_health,
        'domain_dynamics_scale':domain.dynamics_scale,
    }
    for i in range(cfg.n_auv):
        row[f'auv{i}_x']=env.auv_pos[i,0];row[f'auv{i}_y']=env.auv_pos[i,1]
        row[f'auv{i}_aoi']=env.aoi[i];row[f'auv{i}_per']=env.per_ema[i]
    rows.append(row)

record(-1,info,DomainConfig(),0,.98)
start=time.perf_counter()
while env.step_id<cfg.max_steps:
    step=env.step_id
    domain=_domain_for(scenario,step,cfg.max_steps,1.0)
    action=controller.act(obs,info)
    previous_learning=env.learning_bytes
    confidence=float(np.clip(np.exp(-float(np.mean(env.aoi))/2.2)*(1-float(np.mean(env.per_ema))),0,1))
    next_obs,_,done,next_info=env.step(action,domain,planner=planner,drift=controller.drift_score,learning_active=controller.learning_active)
    controller.feedback(obs,next_obs,action,next_info)
    record(step,next_info,domain,previous_learning,confidence)
    obs,info=next_obs,next_info
    if done:break
frame=pd.DataFrame(rows)
frame.to_csv(OUT/'trace.csv',index=False)
metrics=env.summary();metrics.update(_capture_profiles(env,scenario));metrics.update(controller.summary())
metadata={
    'source':'Fresh numerical simulation of supplied source and checkpoint. This is an illustrative episode, not field footage or an aggregate benchmark.',
    'scenario':scenario,'seed':seed,'method':method,'planner':planner,'backbone':'td3','strength':1.0,
    'config':asdict(cfg),'torch':torch.__version__,'python':platform.python_version(),'device':args.device,'numpy':np.__version__,
    'seconds':time.perf_counter()-start,'trace_rows':len(frame),
    'time_convention':'Initial state is step=-1,time_s=0; subsequent rows are after step(), time_s=(step+1)*dt.',
    'checkpoint_sha256':hashlib.sha256(checkpoint.read_bytes()).hexdigest(),
    'code_sha256':{str(p.relative_to(ROOT)):hashlib.sha256(p.read_bytes()).hexdigest() for p in [ROOT/'campe/config.py',ROOT/'campe/environment.py',ROOT/'campe/policy.py',ROOT/'campe/experiment.py']},
    'summary':metrics,'checkpoint_parameters':sum(p.numel() for p in controller.backbone.parameters()),
    'field_notes':{
       'control_ratio':'Reservation ratio, not actual byte consumption.',
       'telemetry_bytes_step':'Adaptation-status telemetry bytes; local learning does not depend on delivery.',
       'planner_confidence_before_step':'Formula evaluated using cached AoI/PER immediately before step; decision only occurs on replanning ticks.',
       'domain_*':'Simulator truth for visualization labels only; never supplied as a controller input.',
       'score':'Instantaneous formation score; capture outcome requires the full persistent-window protocol.',
       'per':'Mean exponentially smoothed link packet-error estimate, not aggregate packet_losses/packet_attempts.'
    }
}
(OUT/'trace_metadata.json').write_text(json.dumps(metadata,indent=2))
print(json.dumps({k:metadata[k] for k in ['scenario','seed','torch','seconds','trace_rows']},indent=2))
print(json.dumps({k:metrics[k] for k in ['mission_outcome_medium','mission_outcome_strict','formation_score','final_performance','aoi','per','adapter_parameters','usv_distance']},indent=2))
