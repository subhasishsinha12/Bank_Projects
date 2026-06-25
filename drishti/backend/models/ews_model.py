def compute_ews_stage(pd_current, bureau_dpd, dscr):
    if pd_current > 0.5 or bureau_dpd >= 60:
        return 'RED'
    elif pd_current > 0.25 or bureau_dpd >= 30 or dscr < 1.1:
        return 'AMBER'
    return 'GREEN'


def compute_inas_stage(pd_current, ews_stage):
    if pd_current > 0.6:
        return 'Stage 3'
    elif pd_current > 0.25 or ews_stage == 'RED':
        return 'Stage 2'
    return 'Stage 1'
