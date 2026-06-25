export const colors = {
  navy:     '#050D1A',
  navy2:    '#0A1628',
  navy3:    '#0F1F38',
  navy4:    '#162848',
  gold:     '#C9A84C',
  goldBr:   '#E8C96A',
  goldDim:  '#7A6230',
  electric: '#4FC3F7',
  mint:     '#50E3C2',
  violet:   '#A78BFA',
  crimson:  '#FF5B5B',
  textPri:  '#E8E2D4',
  textSec:  '#9A9080',
  textMut:  '#5A5448',
  viveka:   '#4FC3F7',
  raksha:   '#50E3C2',
  satya:    '#A78BFA',
};

export const psiColor = (psi) => {
  if (psi >= 0.25) return colors.crimson;
  if (psi >= 0.10) return '#F59E0B';
  return colors.mint;
};

export const ewsColor = (stage) => {
  if (stage === 'RED') return colors.crimson;
  if (stage === 'AMBER') return '#F59E0B';
  return colors.mint;
};

export const stageColor = (stage) => {
  if (stage === 'Stage 3') return colors.crimson;
  if (stage === 'Stage 2') return '#F59E0B';
  return colors.mint;
};

export const dirColor = (dir) => {
  if (dir >= 0.90) return colors.mint;
  if (dir >= 0.80) return '#F59E0B';
  return colors.crimson;
};
