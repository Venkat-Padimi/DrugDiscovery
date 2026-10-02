import Plotly from 'plotly.js-dist-min';
import createPlotComponent from 'react-plotly.js/factory';

// Create ESM-compatible Plotly component
const Plot = createPlotComponent(Plotly);

export default Plot;
