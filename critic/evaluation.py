"""Exploratory software-run comparison, never unlabeled diagnostic accuracy."""
def compare_modes(baseline,agent):
    history=agent.get('hypothesis_history',[])
    findings=[i for h in history for i in (h.get('review') or {}).get('issues',[])]
    initial=baseline['candidates'];final=agent['disease_candidates']
    return dict(
        interpretation='Exploratory workflow comparison; additional tools and Controller may also affect the outcome. No clinical accuracy or causal Critic-effect claim.',
        baseline=dict(steps=baseline.get('steps'),tool_calls=baseline.get('tool_calls'),elapsed_seconds=baseline.get('elapsed_seconds'),candidate_ids=[c['id'] for c in initial],critic_conflicts_detected=None,unsupported_claims_flagged=None),
        autonomous=dict(steps=agent['iteration'],tool_calls=sum(t['status'] in ('completed','failed') for t in agent['tool_history']),elapsed_seconds=agent.get('elapsed_seconds'),candidate_ids=[c['id'] for c in final],critic_conflicts_detected=sum(i['code']=='OBSERVATION_MISMATCH' for i in findings),unsupported_claims_flagged=sum(i['code']=='UNSUPPORTED_CLAIM' for i in findings),abstained=agent['status']=='abstained',status=agent['status']),
        candidate_ids_changed={c['id'] for c in initial}!={c['id'] for c in final},claims_changed=initial!=final,diagnostic_accuracy=None,ground_truth_labels_available=False)
