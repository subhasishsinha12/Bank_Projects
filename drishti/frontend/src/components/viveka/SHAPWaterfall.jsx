import React from 'react';
import Plot from 'react-plotly.js';
import { colors } from '../../utils/colors';

export default function SHAPWaterfall({ shapValues, baseValue, finalPD }) {
  if (!shapValues || shapValues.length === 0) return null;

  const sorted = [...shapValues].sort((a, b) => Math.abs(b.shap) - Math.abs(a.shap)).slice(0, 8);

  const measures = ['absolute', ...sorted.map(() => 'relative'), 'total'];
  const xVals = [baseValue, ...sorted.map(v => v.shap), finalPD];
  const yVals = ['Base Rate', ...sorted.map(v => v.feature.replace(/_/g, ' ')), 'Final PD'];

  const data = [{
    type: 'waterfall',
    orientation: 'h',
    measure: measures,
    x: xVals,
    y: yVals,
    connector: { line: { color: 'rgba(201,168,76,0.3)' } },
    increasing: { marker: { color: colors.crimson } },
    decreasing: { marker: { color: colors.electric } },
    totals: { marker: { color: colors.gold } },
    textfont: { family: 'IBM Plex Mono', color: colors.textPri, size: 11 },
    textposition: 'outside',
  }];

  const layout = {
    paper_bgcolor: colors.navy3,
    plot_bgcolor: colors.navy3,
    font: { family: 'IBM Plex Mono', color: colors.textSec, size: 11 },
    xaxis: {
      gridcolor: 'rgba(201,168,76,0.1)',
      tickformat: '.1%',
      color: colors.textSec,
      tickfont: { size: 10 },
    },
    yaxis: {
      gridcolor: 'rgba(201,168,76,0.1)',
      color: colors.textSec,
      tickfont: { size: 10 },
      automargin: true,
    },
    margin: { l: 130, r: 60, t: 20, b: 40 },
    height: 380,
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
