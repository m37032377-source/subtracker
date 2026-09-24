// Построение графиков на странице аналитики с помощью Chart.js.
// Данные передаются из Django через тег json_script (безопасно, без eval).
document.addEventListener('DOMContentLoaded', () => {
  const data = JSON.parse(document.getElementById('chart-data').textContent);
  const monthNames = ['янв', 'фев', 'мар', 'апр', 'май', 'июн', 'июл', 'авг', 'сен', 'окт', 'ноя', 'дек'];

  // "2026-03" -> "мар 2026"
  const formatMonth = (key) => {
    const [year, month] = key.split('-');
    return `${monthNames[Number(month) - 1]} ${year}`;
  };

  new Chart(document.getElementById('monthsChart'), {
    type: 'bar',
    data: {
      labels: data.months.labels.map(formatMonth),
      datasets: [{ label: 'Расходы', data: data.months.values, backgroundColor: '#4f46e5', borderRadius: 6 }],
    },
    options: {
      maintainAspectRatio: false,
      plugins: { legend: { display: false } },
      scales: { y: { beginAtZero: true } },
    },
  });

  new Chart(document.getElementById('categoriesChart'), {
    type: 'doughnut',
    data: {
      labels: data.categories.labels,
      datasets: [{ data: data.categories.values, backgroundColor: data.categories.colors }],
    },
    options: { maintainAspectRatio: false, plugins: { legend: { position: 'bottom' } } },
  });
});
