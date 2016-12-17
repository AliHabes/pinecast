(function() {
var hr = document.querySelector('.host-rows');

document.querySelector('.add-host').addEventListener('click', function(e) {
  e.preventDefault();
  addHost();
});
function addHost() {
  var tpl = document.querySelector('.host-template');
  var clone = document.importNode(tpl.content, true);
  hr.appendChild(clone);
  serHostBlob();
}

if (hr.childNodes.length === 0) {
  addHost();
}

hr.addEventListener('input', function() {
  serHostBlob();
});
hr.addEventListener('click', function(e) {
  var elem = e.target;
  while (true) {
    if (elem === hr) {
      return;
    }
    if (elem.type === 'button') {
      break;
    }
    elem = elem.parentNode;
  }
  while (elem.className !== 'host-row') {
    elem = elem.parentNode;
  }
  e.preventDefault();
  elem.parentNode.removeChild(elem);
  serHostBlob();
});

function serHostBlob() {
  var blob = [];
  Array.prototype.slice.call(document.querySelectorAll('.host-row')).forEach(function(row) {
    var data = {
      name: row.querySelector('[data-type=name]').value,
      email: row.querySelector('[data-type=email]').value,
    };
    Array.prototype.slice.call(row.querySelectorAll('[data-contact-type]')).forEach(function(input) {
      if (!input.value) {
        return;
      }
      data[input.getAttribute('data-contact-type')] = input.value;
    });
    blob.push(data);
  });
  document.querySelector('[name=host_blob]').value = JSON.stringify(blob);

  hr.className = hr.querySelectorAll('.host-row').length > 1 ? 'host-rows' : 'host-rows only-one';
}

}());
