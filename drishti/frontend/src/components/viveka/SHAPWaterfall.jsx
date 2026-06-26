import React from 'react';
import Plot from 'react-plotly.js';
import { colors } from '../../utils/colors';

export default function SHAPWaterfall({ shapValues, baseValue, finalPD }) {
  if (!shapValues || shapValues.length === 0) return null;

  const sorted = [...shapValues]
    .sort((a, b) => Math.abs(b.shap) - Math.abs(a.shap))
    .slice(0, 8);

  const measures = ['absolute', ...sorted.map(() => 'relative'), 'total'];
  const xVals = [baseValue, ...sorted.map(v => v.shap), finalPD];
  const yVals = ['Base Rate', ...sorted.map(v => v.feature.replace(/_/g, ' ')), 'Final PD'];

  const data = [{
    type: 'waterfall',
    orientation: 'h',
    measure: measures,
    x: xVals,
    y: yVals,
    connector: { line: { color: 'rgba(201,168,76,0.2)', width: 1, dash: 'dot' } },
    increasing: { marker: { color: 'rgba(255,91,91,0.85)', line: { color: colors.crimson, width: 1 } } },
    decreasing: { marker: { color: 'rgba(79,195,247,0.85)', line: { color: colors.electric, width: 1 } } },
    totals: { marker: { color: 'rgba(201,168,76,0.85)', line: { color: colors.gold, width: 1 } } },
    textfont: { family: 'IBM Plex Mono', color: colors.textSec, size: 10 },
    textposition: 'outside',
  }];

  const layout = {
    paper_bgcolor: 'transparent',
    plot_bgcolor: 'transparent',
    font: { family: 'IBM Plex Mono', color: colors.textSec, size: 10 },
    xaxis: {
      gridcolor: 'rgba(201,168,76,0.06)',
      tickformat: '.1%',
      color: colors.textMut,
      tickfont: { size: 9 },
      zeroline: true,
      zerolinecolor: 'rgba(201,168,76,0.15)',
    },
    yaxis: {
      gridcolor: 'rgba(201,168,76,0.06)',
      color: colors.textMut,
      tickfont: { size: 9 },
      automargin: true,
    },
    margin: { l: 130, r: 50, t: 10, b: 30 },
    height: 340,
  };

  return (
    <Plot
      data={data}
      layout={layout}
      config={{ displayModeBar: false, responsive: true }}
      style={{ width: '100%' }}
    />
  );
}
