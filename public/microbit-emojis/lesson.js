const patterns = {
  happy: ['00000', '01010', '00000', '10001', '01110'],
  sad: ['00000', '01010', '00000', '01110', '10001'],
  heart: ['01010', '11111', '11111', '01110', '00100'],
  clear: ['00000', '00000', '00000', '00000', '00000']
};
let pixels = patterns.happy.join('').split('').map(value => value === '1');
const grid = document.querySelector('#led-grid');
const buttons = pixels.map((_, index) => {
  const button = document.createElement('button');
  button.type = 'button';
  button.setAttribute('aria-label', `Σειρά ${Math.floor(index / 5) + 1}, στήλη ${index % 5 + 1}`);
  button.addEventListener('click', () => { pixels[index] = !pixels[index]; render(); });
  grid.append(button);
  return button;
});
function render() {
  buttons.forEach((button, index) => button.setAttribute('aria-pressed', String(pixels[index])));
  document.querySelector('#pattern-output').textContent = Array.from({length: 5}, (_, row) =>
    pixels.slice(row * 5, row * 5 + 5).map(on => on ? '#' : '.').join(' ')).join('\n');
  document.querySelector('#led-status').textContent = `${pixels.filter(Boolean).length} από τα 25 LED αναμμένα.`;
}
document.querySelectorAll('[data-pattern]').forEach(button => {
  button.addEventListener('click', () => {
    pixels = patterns[button.dataset.pattern].join('').split('').map(value => value === '1');
    render();
  });
});
render();
