export const colors = {
  bg:       '#020810',
  bg2:      '#05101E',
  bg3:      '#081528',
  bg4:      '#0C1C35',
  bg5:      '#112244',
  navy:     '#050D1A',
  navy2:    '#0A1628',
  navy3:    '#0F1F38',
  navy4:    '#162848',
  gold:     '#C9A84C',
  goldBr:   '#E8C96A',
  goldDim:  '#7A6230',
  goldMut:  'rgba(201,168,76,0.12)',
  electric: '#4FC3F7',
  mint:     '#50E3C2',
  violet:   '#A78BFA',
  crimson:  '#FF5B5B',
  amber:    '#F59E0B',
  textPri:  '#EDE8DC',
  textSec:  '#8A8070',
  textMut:  '#4A4438',
  viveka:   '#4FC3F7',
  raksha:   '#50E3C2',
  satya:    '#A78BFA',
};

export const moduleColors = {
  viveka: { primary: '#4FC3F7', secondary: '#0288D1', glow: 'rgba(79,195,247,0.15)', border: 'rgba(79,195,247,0.2)' },
  raksha: { primary: '#50E3C2', secondary: '#26A69A', glow: 'rgba(80,227,194,0.15)', border: 'rgba(80,227,194,0.2)' },
  satya:  { primary: '#A78BFA', secondary: '#7C3AED', glow: 'rgba(167,139,250,0.15)', border: 'rgba(167,139,250,0.2)' },
};

export const psiColor = (psi) => {
  if (psi >= 0.25) return colors.crimson;
  if (psi >= 0.10) return colors.amber;
  return colors.mint;
};

export const psiGlow = (psi) => {
  if (psi >= 0.25) return 'rgba(255,91,91,0.2)';
  if (psi >= 0.10) return 'rgba(245,158,11,0.2)';
  return 'rgba(80,227,194,0.2)';
};

export const ewsColor = (stage) => {
  if (stage === 'RED') return colors.crimson;
  if (stage === 'AMBER') return colors.amber;
  return colors.mint;
};

export const ewsBg = (stage) => {
  if (stage === 'RED') return 'rgba(255,91,91,0.1)';
  if (stage === 'AMBER') return 'rgba(245,158,11,0.1)';
  return 'rgba(80,227,194,0.1)';
};

export const stageColor = (stage) => {
  if (stage === 'Stage 3') return colors.crimson;
  if (stage === 'Stage 2') return colors.amber;
  return colors.mint;
};

export const dirColor = (dir) => {
  if (dir >= 0.90) return colors.mint;
  if (dir >= 0.80) return colors.amber;
  return colors.crimson;
};

export const pdColor = (pd) => {
  if (pd > 0.40) return colors.crimson;
  if (pd > 0.20) return colors.amber;
  return colors.mint;
};
