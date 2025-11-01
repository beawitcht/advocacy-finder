document.addEventListener('DOMContentLoaded', () => {
    const form = document.getElementById('search-form');
    const postcodeInput = document.getElementById('postcode');
    const container = document.getElementById('address-container');

    form.addEventListener('submit', async (e) => {
        e.preventDefault();
        container.textContent = '';
        const postcode = postcodeInput.value.trim();
        if (!postcode) {
            container.textContent = 'Please enter a postcode.';
            return;
        }

        container.textContent = 'Searching...';

        const url = 'https://www.gov.uk/api/local-authority?postcode=' + encodeURIComponent(postcode);

        try {
            const res = await fetch(url);
            if (!res.ok) {
                const txt = await res.text();
                container.innerHTML = `<div>Error: ${res.status} ${res.statusText}</div><pre>${escapeHtml(txt)}</pre>`;
                return;
            }
            const data = await res.json();
            container.innerHTML = `<pre>${JSON.stringify(data, null, 2)}</pre>`;
        } catch (err) {
            container.textContent = 'Network error: ' + err.message;
        }
    });


});