/* ==========================================================================
   Verity - Visualizations Tab (Chart.js + Plotly.js)
   ========================================================================== */

const _chartInstances = {};
let _vizInitialized = false;
let _vizData = null;

function _cssVar(name, fallback) {
  const val = getComputedStyle(document.body).getPropertyValue(name).trim();
  return val || fallback;
}

function _themePalette() {
  const isLight = document.body.classList.contains('light');
  return {
    isLight,
    textPrimary: _cssVar('--text-primary', isLight ? '#0f172a' : '#f1f5f9'),
    textMuted: _cssVar('--text-muted', isLight ? '#64748b' : '#8899b5'),
    gridColor: isLight ? 'rgba(15, 23, 42, 0.08)' : 'rgba(148, 163, 184, 0.14)',
    surface: _cssVar('--bg-surface', isLight ? '#ffffff' : '#131b2e'),
    canvasBg: _cssVar('--bg-canvas', isLight ? '#f1f5f9' : '#0d121f'),
    primary: _cssVar('--primary-500', isLight ? '#2563eb' : '#3b82f6'),
    success: _cssVar('--success-text', '#34d399'),
    warning: _cssVar('--warning-text', '#fbbf24'),
    danger: _cssVar('--danger-text', '#f87171'),
    info: _cssVar('--info-text', '#60a5fa'),
    purple: isLight ? '#7c3aed' : '#a78bfa',
    teal: isLight ? '#0d9488' : '#2dd4bf',
    tooltipBg: isLight ? '#0f172a' : '#0a0f1d',
    tooltipBorder: isLight ? '#cbd5e1' : '#2a3b5c',
  };
}

function _destroyChart(key) {
  if (_chartInstances[key]) {
    _chartInstances[key].destroy();
    delete _chartInstances[key];
  }
}

function _formatNum(val) {
  if (val === null || val === undefined || Number.isNaN(val)) return 'N/A';
  const n = Number(val);
  if (Number.isInteger(n)) return n.toLocaleString();
  return n.toLocaleString(undefined, { maximumFractionDigits: 3 });
}

function _vizEscape(str) {
  return String(str ?? '')
    .replace(/&/g, '&amp;')
    .replace(/</g, '&lt;')
    .replace(/>/g, '&gt;')
    .replace(/"/g, '&quot;');
}

function _setLoading(show) {
  const loader = document.getElementById('vizLoading');
  if (loader) loader.style.display = show ? 'flex' : 'none';
}

function _renderQualityOverview(dq) {
  const kpiEl = document.getElementById('vizQualityKpis');
  const issuesEl = document.getElementById('vizQualityIssues');
  if (!kpiEl || !issuesEl) return;

  kpiEl.innerHTML = `
    <div class="viz-kpi-card">
      <div class="viz-kpi-label">Total Records</div>
      <div class="viz-kpi-val">${(dq.total_records ?? 0).toLocaleString()}</div>
      <div class="viz-kpi-sub">Uploaded dataset rows</div>
    </div>
    <div class="viz-kpi-card">
      <div class="viz-kpi-label">Total Columns</div>
      <div class="viz-kpi-val">${(dq.total_columns ?? 0).toLocaleString()}</div>
      <div class="viz-kpi-sub">Schema fields profiled</div>
    </div>
    <div class="viz-kpi-card">
      <div class="viz-kpi-label">Missing Values</div>
      <div class="viz-kpi-val" style="color:${dq.missing_values > 0 ? 'var(--warning-text)' : 'var(--success-text)'}">${(dq.missing_values ?? 0).toLocaleString()}</div>
      <div class="viz-kpi-sub">${dq.missing_pct ?? 0}% of all cells</div>
    </div>
    <div class="viz-kpi-card">
      <div class="viz-kpi-label">Duplicate Records</div>
      <div class="viz-kpi-val" style="color:${dq.duplicate_records > 0 ? 'var(--warning-text)' : 'var(--success-text)'}">${(dq.duplicate_records ?? 0).toLocaleString()}</div>
      <div class="viz-kpi-sub">Exact duplicate rows</div>
    </div>
    <div class="viz-kpi-card">
      <div class="viz-kpi-label">Undocumented Fields</div>
      <div class="viz-kpi-val" style="color:${dq.undocumented_fields > 0 ? 'var(--warning-text)' : 'var(--success-text)'}">${(dq.undocumented_fields ?? 0).toLocaleString()}</div>
      <div class="viz-kpi-sub">Not sent to LLM (Code gate)</div>
    </div>
  `;

  const sev = dq.severity_counts || { high: 0, medium: 0, low: 0 };
  const issues = dq.issues || [];
  let html = `
    <div class="viz-issues-header">
      <span class="viz-issues-title">Detected Data Quality Issues (${dq.total_issues ?? issues.length})</span>
      <div class="viz-sev-pills">
        <span class="severity sev-high">High: ${sev.high || 0}</span>
        <span class="severity sev-medium">Medium: ${sev.medium || 0}</span>
        <span class="severity sev-low">Low: ${sev.low || 0}</span>
      </div>
    </div>
  `;

  if (!issues.length) {
    html += `<div class="viz-empty-inline" style="color:var(--success-text)">✅ No data quality issues detected across all rules.</div>`;
  } else {
    html += '<div class="viz-issues-list">';
    issues.forEach(item => {
      const s = (item.severity || 'low').toLowerCase();
      const sevCls = s === 'high' ? 'sev-high' : s === 'medium' ? 'sev-medium' : 'sev-low';
      html += `
        <div class="viz-issue-row">
          <span class="severity ${sevCls}">${_vizEscape(item.severity)}</span>
          <span class="badge badge-gray">${_vizEscape(item.rule_id)}</span>
          <div class="viz-issue-body">
            <div class="viz-issue-title">${_vizEscape(item.title)}</div>
            <div class="viz-issue-evidence">${_vizEscape(item.evidence)}</div>
          </div>
        </div>
      `;
    });
    html += '</div>';
  }
  issuesEl.innerHTML = html;
}

function _renderDataTypes(dt) {
  const pal = _themePalette();
  const counts = dt.counts || {};
  const labels = ['Numerical', 'Categorical', 'Date/Time', 'Other'];
  const values = labels.map(k => counts[k] || 0);
  const total = values.reduce((a, b) => a + b, 0);

  const metaEl = document.getElementById('vizDataTypesMeta');
  if (metaEl) {
    metaEl.innerHTML = labels.map(l => `<span class="badge badge-gray">${l}: ${counts[l] || 0}</span>`).join(' ');
  }

  const canvas = document.getElementById('vizDataTypesChart');
  if (!canvas) return;
  _destroyChart('dataTypes');

  if (!total) {
    canvas.parentElement.innerHTML = '<div class="viz-empty-inline">No columns detected for data type distribution.</div>';
    return;
  }

  _chartInstances.dataTypes = new Chart(canvas, {
    type: 'doughnut',
    data: {
      labels,
      datasets: [{
        data: values,
        backgroundColor: [pal.primary, pal.purple, pal.teal, pal.warning],
        borderColor: pal.surface,
        borderWidth: 3,
        hoverOffset: 6,
      }],
    },
    options: {
      responsive: true,
      maintainAspectRatio: false,
      cutout: '64%',
      plugins: {
        legend: {
          position: 'bottom',
          labels: { color: pal.textPrimary, padding: 14, usePointStyle: true },
        },
        tooltip: {
          backgroundColor: pal.tooltipBg,
          borderColor: pal.tooltipBorder,
          borderWidth: 1,
          callbacks: {
            label: ctx => {
              const val = ctx.parsed || 0;
              const pct = total ? ((val / total) * 100).toFixed(1) : '0.0';
              return ` ${ctx.label}: ${val} columns (${pct}%)`;
            },
          },
        },
      },
    },
  });
}

function _renderNumericalColumn(colName) {
  if (!_vizData || !_vizData.numerical_analysis) return;
  const pal = _themePalette();
  const colData = _vizData.numerical_analysis.by_column[colName];
  const statsEl = document.getElementById('vizNumStats');
  const histCanvas = document.getElementById('vizNumHistChart');
  const boxDiv = document.getElementById('vizNumBoxPlot');
  if (!statsEl || !histCanvas || !boxDiv) return;

  if (!colData || colData.count === 0) {
    statsEl.innerHTML = '<div class="viz-empty-inline">Selected column contains no valid numerical values.</div>';
    _destroyChart('numHist');
    if (window.Plotly) Plotly.purge(boxDiv);
    boxDiv.innerHTML = '<div class="viz-empty-inline">No data for box plot.</div>';
    return;
  }

  statsEl.innerHTML = `
    <div class="viz-mini-stat"><span>Min</span><strong>${_formatNum(colData.min)}</strong></div>
    <div class="viz-mini-stat"><span>Max</span><strong>${_formatNum(colData.max)}</strong></div>
    <div class="viz-mini-stat"><span>Mean</span><strong>${_formatNum(colData.mean)}</strong></div>
    <div class="viz-mini-stat"><span>Median</span><strong>${_formatNum(colData.median)}</strong></div>
    <div class="viz-mini-stat"><span>Std Dev</span><strong>${_formatNum(colData.std)}</strong></div>
    <div class="viz-mini-stat"><span>Valid / Outliers</span><strong>${colData.count.toLocaleString()} / ${colData.outlier_count.toLocaleString()}</strong></div>
  `;

  // Histogram (Chart.js)
  _destroyChart('numHist');
  _chartInstances.numHist = new Chart(histCanvas, {
    type: 'bar',
    data: {
      labels: colData.histogram.labels,
      datasets: [{
        label: 'Frequency',
        data: colData.histogram.counts,
        backgroundColor: pal.primary,
        borderColor: pal.primary,
        borderRadius: 4,
      }],
    },
    options: {
      responsive: true,
      maintainAspectRatio: false,
      plugins: {
        legend: { display: false },
        title: {
          display: true,
          text: `Histogram: ${colName}`,
          color: pal.textPrimary,
          font: { size: 13, weight: '600' },
        },
        tooltip: {
          backgroundColor: pal.tooltipBg,
          borderColor: pal.tooltipBorder,
          borderWidth: 1,
          callbacks: {
            label: ctx => ` Count: ${(ctx.parsed.y || 0).toLocaleString()}`,
          },
        },
      },
      scales: {
        x: {
          grid: { display: false },
          ticks: { color: pal.textMuted, maxRotation: 40, minRotation: 0 },
          title: { display: true, text: 'Value Bins', color: pal.textMuted },
        },
        y: {
          beginAtZero: true,
          grid: { color: pal.gridColor },
          ticks: { color: pal.textMuted },
          title: { display: true, text: 'Record Count', color: pal.textMuted },
        },
      },
    },
  });

  // Box Plot (Plotly.js)
  if (typeof Plotly === 'undefined') {
    boxDiv.innerHTML = '<div class="viz-empty-inline">Plotly.js failed to load.</div>';
    return;
  }

  boxDiv.innerHTML = '';
  const traces = [{
    type: 'box',
    name: colName,
    x: [colName],
    q1: [colData.q1],
    median: [colData.median],
    q3: [colData.q3],
    lowerfence: [colData.lowerfence],
    upperfence: [colData.upperfence],
    mean: [colData.mean],
    sd: [colData.std],
    boxmean: 'sd',
    marker: { color: pal.primary },
    line: { color: pal.primary, width: 2 },
    fillcolor: pal.isLight ? 'rgba(37, 99, 235, 0.18)' : 'rgba(59, 130, 246, 0.25)',
    hoverinfo: 'y+name',
  }];

  if (colData.outliers && colData.outliers.length) {
    traces.push({
      type: 'scatter',
      mode: 'markers',
      name: `Outliers (${colData.outlier_count})`,
      x: colData.outliers.map(() => colName),
      y: colData.outliers,
      marker: { color: pal.danger, size: 6, opacity: 0.72 },
      hovertemplate: `${_vizEscape(colName)}: %{y}<extra>Outlier</extra>`,
    });
  }

  Plotly.newPlot(boxDiv, traces, {
    title: { text: `Box Plot: ${colName}`, font: { size: 13, color: pal.textPrimary } },
    paper_bgcolor: 'rgba(0,0,0,0)',
    plot_bgcolor: 'rgba(0,0,0,0)',
    font: { color: pal.textMuted, family: 'inherit' },
    margin: { t: 42, r: 20, b: 40, l: 55 },
    showlegend: colData.outliers && colData.outliers.length > 0,
    legend: { orientation: 'h', y: -0.18, font: { color: pal.textMuted } },
    xaxis: { tickfont: { color: pal.textPrimary }, gridcolor: pal.gridColor },
    yaxis: { tickfont: { color: pal.textMuted }, gridcolor: pal.gridColor, zerolinecolor: pal.gridColor },
  }, { responsive: true, displaylogo: false });
}

function _renderCategoricalColumn(colName) {
  if (!_vizData || !_vizData.categorical_analysis) return;
  const pal = _themePalette();
  const colData = _vizData.categorical_analysis.by_column[colName];
  const metaEl = document.getElementById('vizCatMeta');
  const canvas = document.getElementById('vizCatChart');
  if (!metaEl || !canvas) return;

  if (!colData || colData.total_non_null === 0) {
    metaEl.innerHTML = '<span class="badge badge-gray">No non-null values</span>';
    _destroyChart('catFreq');
    return;
  }

  metaEl.innerHTML = `
    <span class="badge badge-blue">Unique Categories: ${colData.unique_count.toLocaleString()}</span>
    <span class="badge badge-gray">Non-Null Records: ${colData.total_non_null.toLocaleString()}</span>
    <span class="badge badge-green">Top: ${_vizEscape(colData.top_category)} (${colData.top_count.toLocaleString()})</span>
    ${colData.truncated ? `<span class="badge badge-amber">Showing top ${colData.labels.length} of ${colData.unique_count.toLocaleString()}</span>` : ''}
  `;

  _destroyChart('catFreq');
  _chartInstances.catFreq = new Chart(canvas, {
    type: 'bar',
    data: {
      labels: colData.labels,
      datasets: [{
        label: 'Frequency',
        data: colData.counts,
        backgroundColor: pal.purple,
        borderRadius: 5,
      }],
    },
    options: {
      responsive: true,
      maintainAspectRatio: false,
      plugins: {
        legend: { display: false },
        title: {
          display: true,
          text: `Category Frequencies: ${colName}`,
          color: pal.textPrimary,
          font: { size: 13, weight: '600' },
        },
        tooltip: {
          backgroundColor: pal.tooltipBg,
          borderColor: pal.tooltipBorder,
          borderWidth: 1,
          callbacks: {
            label: ctx => {
              const idx = ctx.dataIndex;
              const cnt = colData.counts[idx] ?? 0;
              const pct = colData.percentages[idx] ?? 0;
              return ` Count: ${cnt.toLocaleString()} (${pct}%)`;
            },
          },
        },
      },
      scales: {
        x: {
          grid: { display: false },
          ticks: { color: pal.textPrimary, maxRotation: 35, minRotation: 0 },
        },
        y: {
          beginAtZero: true,
          grid: { color: pal.gridColor },
          ticks: { color: pal.textMuted },
          title: { display: true, text: 'Record Count', color: pal.textMuted },
        },
      },
    },
  });
}

function _renderCorrelationHeatmap(corr) {
  const pal = _themePalette();
  const plotDiv = document.getElementById('vizCorrPlot');
  if (!plotDiv) return;

  if (!corr || !corr.columns || corr.columns.length < 2) {
    plotDiv.innerHTML = '<div class="viz-empty-inline">At least 2 numerical columns are required to compute a correlation heatmap.</div>';
    return;
  }
  if (typeof Plotly === 'undefined') {
    plotDiv.innerHTML = '<div class="viz-empty-inline">Plotly.js failed to load.</div>';
    return;
  }

  plotDiv.innerHTML = '';
  const cols = corr.columns;
  const z = corr.matrix;
  const textMatrix = z.map(row => row.map(v => (v === null || v === undefined ? 'N/A' : Number(v).toFixed(2))));

  const annotations = [];
  for (let i = 0; i < cols.length; i++) {
    for (let j = 0; j < cols.length; j++) {
      const val = z[i][j];
      const txtColor = val !== null && Math.abs(val) > 0.55 ? '#ffffff' : pal.textPrimary;
      annotations.push({
        x: cols[j],
        y: cols[i],
        text: textMatrix[i][j],
        showarrow: false,
        font: { size: cols.length > 10 ? 10 : 12, color: txtColor },
      });
    }
  }

  Plotly.newPlot(plotDiv, [{
    type: 'heatmap',
    z,
    x: cols,
    y: cols,
    zmin: -1,
    zmax: 1,
    colorscale: 'RdBu',
    reversescale: true,
    hoverongaps: false,
    hovertemplate: '%{y} vs %{x}<br>Pearson r: %{z:.3f}<extra></extra>',
    colorbar: {
      title: { text: 'r', font: { color: pal.textPrimary } },
      tickfont: { color: pal.textMuted },
    },
  }], {
    paper_bgcolor: 'rgba(0,0,0,0)',
    plot_bgcolor: 'rgba(0,0,0,0)',
    font: { color: pal.textPrimary, family: 'inherit' },
    margin: { t: 24, r: 24, b: 90, l: 100 },
    annotations,
    xaxis: { tickangle: -30, tickfont: { color: pal.textPrimary }, side: 'bottom' },
    yaxis: { autorange: 'reversed', tickfont: { color: pal.textPrimary } },
  }, { responsive: true, displaylogo: false });
}

function renderAllVisualizations() {
  const container = document.getElementById('tab-viz');
  if (!container || !_vizData) return;

  if (typeof Chart === 'undefined') {
    container.innerHTML = '<div class="viz-error-card">Chart.js failed to load. Please refresh the page.</div>';
    return;
  }

  _setLoading(true);
  try {
    _renderQualityOverview(_vizData.data_quality);
    _renderDataTypes(_vizData.data_types);

    const numSel = document.getElementById('vizNumSelect');
    if (numSel && _vizData.numerical_analysis.columns.length) {
      _renderNumericalColumn(numSel.value || _vizData.numerical_analysis.columns[0]);
    }

    const catSel = document.getElementById('vizCatSelect');
    if (catSel && _vizData.categorical_analysis.columns.length) {
      _renderCategoricalColumn(catSel.value || _vizData.categorical_analysis.columns[0]);
    }

    _renderCorrelationHeatmap(_vizData.correlation);
    _vizInitialized = true;
  } catch (err) {
    console.error('Visualization error:', err);
    const errBox = document.getElementById('vizErrorBanner');
    if (errBox) {
      errBox.style.display = 'block';
      errBox.textContent = 'Error rendering visualizations: ' + err.message;
    }
  } finally {
    _setLoading(false);
  }
}

function resizeVisualizations() {
  Object.values(_chartInstances).forEach(ch => {
    try { ch.resize(); } catch (_) {}
  });
  if (typeof Plotly !== 'undefined') {
    ['vizNumBoxPlot', 'vizCorrPlot'].forEach(id => {
      const el = document.getElementById(id);
      if (el && el.data) {
        try { Plotly.Plots.resize(el); } catch (_) {}
      }
    });
  }
}

function activateVisualizationsTab() {
  if (!_vizInitialized) {
    renderAllVisualizations();
  } else {
    requestAnimationFrame(resizeVisualizations);
  }
}

async function initVisualizations(results) {
  const container = document.getElementById('tab-viz');
  if (!container) return;

  let viz = results && results.visualizations;
  if (!viz) {
    try {
      const res = await fetch('/api/visualizations');
      if (res.ok) viz = await res.json();
    } catch (_) {}
  }

  if (!viz) {
    container.innerHTML = `
      <div class="viz-card">
        <div class="viz-empty-inline">
          Visualization metrics are not available for this cached session.
          <a href="/" style="color:var(--primary-500);font-weight:600;margin-left:6px">Re-upload your dataset →</a>
        </div>
      </div>
    `;
    return;
  }

  _vizData = viz;
  const numCols = (viz.numerical_analysis && viz.numerical_analysis.columns) || [];
  const catCols = (viz.categorical_analysis && viz.categorical_analysis.columns) || [];

  container.innerHTML = `
    <div id="vizLoading" class="viz-loading" style="display:none">
      <div class="viz-spinner"></div>
      <span>Generating interactive visualizations…</span>
    </div>
    <div id="vizErrorBanner" class="viz-error-card" style="display:none"></div>

    <!-- Data Quality Overview -->
    <section class="viz-card viz-full">
      <div class="viz-card-head">
        <div>
          <h3>Data Quality Overview</h3>
          <p class="viz-sub">Dataset scale, completeness, duplicates, documentation gaps, and rule-based findings</p>
        </div>
      </div>
      <div id="vizQualityKpis" class="viz-kpi-grid"></div>
      <div id="vizQualityIssues" class="viz-issues-box"></div>
    </section>

    <!-- Data Type Distribution -->
    <section class="viz-card viz-full">
      <div class="viz-card-head">
        <div>
          <h3>Data Type Distribution</h3>
          <p class="viz-sub">Observed column classification across numerical, categorical, date/time, and other types</p>
        </div>
        <div id="vizDataTypesMeta" class="viz-meta-row" style="margin-bottom:0"></div>
      </div>
      <div class="viz-chart-box viz-chart-doughnut">
        <canvas id="vizDataTypesChart"></canvas>
      </div>
    </section>

    <!-- Numerical Data Analysis -->
    <section class="viz-card viz-full">
      <div class="viz-card-head">
        <div>
          <h3>Numerical Data Analysis</h3>
          <p class="viz-sub">Distribution histogram, Tukey box plot, and summary statistics for the selected numerical column</p>
        </div>
        ${numCols.length ? `
          <div class="viz-select-wrap">
            <label for="vizNumSelect">Numerical Column:</label>
            <select id="vizNumSelect" class="viz-select">
              ${numCols.map(c => `<option value="${_vizEscape(c)}">${_vizEscape(c)}</option>`).join('')}
            </select>
          </div>
        ` : ''}
      </div>
      ${numCols.length ? `
        <div id="vizNumStats" class="viz-mini-stats"></div>
        <div class="viz-grid-2" style="margin-top:16px">
          <div class="viz-subpanel">
            <div class="viz-chart-box" style="height:310px">
              <canvas id="vizNumHistChart"></canvas>
            </div>
          </div>
          <div class="viz-subpanel">
            <div id="vizNumBoxPlot" class="viz-plotly-box" style="height:310px"></div>
          </div>
        </div>
      ` : '<div class="viz-empty-inline">No numerical columns found in this dataset.</div>'}
    </section>

    <!-- Categorical Data Analysis -->
    <section class="viz-card viz-full">
      <div class="viz-card-head">
        <div>
          <h3>Categorical Data Analysis</h3>
          <p class="viz-sub">Category frequencies and unique value counts for the selected categorical column</p>
        </div>
        ${catCols.length ? `
          <div class="viz-select-wrap">
            <label for="vizCatSelect">Categorical Column:</label>
            <select id="vizCatSelect" class="viz-select">
              ${catCols.map(c => `<option value="${_vizEscape(c)}">${_vizEscape(c)}</option>`).join('')}
            </select>
          </div>
        ` : ''}
      </div>
      ${catCols.length ? `
        <div id="vizCatMeta" class="viz-meta-row"></div>
        <div class="viz-chart-box" style="height:330px">
          <canvas id="vizCatChart"></canvas>
        </div>
      ` : '<div class="viz-empty-inline">No categorical columns found in this dataset.</div>'}
    </section>

    <!-- Correlation Heatmap -->
    <section class="viz-card viz-full">
      <div class="viz-card-head">
        <div>
          <h3>Correlation Heatmap</h3>
          <p class="viz-sub">Pearson linear correlation matrix computed over numerical columns only</p>
        </div>
      </div>
      <div class="viz-disclaimer">
        ⚠ <strong>Important:</strong> ${(viz.correlation && _vizEscape(viz.correlation.note)) || 'Correlation does not imply causation.'}
      </div>
      <div id="vizCorrPlot" class="viz-plotly-box" style="height:440px"></div>
    </section>
  `;

  const numSel = document.getElementById('vizNumSelect');
  if (numSel) {
    numSel.addEventListener('change', () => _renderNumericalColumn(numSel.value));
  }

  const catSel = document.getElementById('vizCatSelect');
  if (catSel) {
    catSel.addEventListener('change', () => _renderCategoricalColumn(catSel.value));
  }

  // Re-render charts on Dark/Light theme toggle
  const observer = new MutationObserver(() => {
    if (_vizInitialized && container.classList.contains('active')) {
      renderAllVisualizations();
    } else if (_vizInitialized) {
      _vizInitialized = false;
    }
  });
  observer.observe(document.body, { attributes: true, attributeFilter: ['class'] });

  // Render immediately if the tab is already active
  if (container.classList.contains('active')) {
    renderAllVisualizations();
  }
}
