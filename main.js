document.addEventListener('DOMContentLoaded', () => {
    const form = document.getElementById('search-form');
    const postcodeInput = document.getElementById('postcode');
    const container = document.getElementById('address-container');

    function pickDisplayNameFromLocalAuthority(localAuthority) {
        if (!localAuthority) return null;
        if (localAuthority.parent && localAuthority.parent.name) return localAuthority.parent.name;
        return localAuthority.name || null;
    }

    async function fetchJsonOrDetectHtml(url) {
        const res = await fetch(url);
        if (!res.ok) {
            const txt = await res.text();
            return { ok: false, status: res.status, statusText: res.statusText, bodyText: txt };
        }

        const contentType = (res.headers.get('content-type') || '').toLowerCase();
        if (contentType.includes('application/json') || contentType.includes('+json')) {
            const json = await res.json();
            return { ok: true, json };
        }

        // not JSON according to headers — read text and try to detect HTML or parse JSON fallback
        const txt = await res.text();
        if (txt.trim().startsWith('<')) {
            return { ok: false, html: true, bodyText: txt };
        }
        try {
            const json = JSON.parse(txt);
            return { ok: true, json };
        } catch {
            return { ok: false, bodyText: txt };
        }
    }

    form.addEventListener('submit', async (e) => {
        e.preventDefault();
        container.textContent = '';
        const postcode = postcodeInput.value.trim();
        if (!postcode) {
            container.textContent = 'Please enter a postcode.';
            return;
        }

        container.textContent = 'Searching...';

        const target = 'https://www.gov.uk/api/local-authority?postcode=' + encodeURIComponent(postcode);
        const url = 'https://api.allorigins.win/raw?url=' + encodeURIComponent(target);

        try {
            const result = await fetchJsonOrDetectHtml(url);

            if (!result.ok) {
                // HTML response -> Postcode Invalid
                if (result.html || (result.bodyText && result.bodyText.trim().startsWith('<'))) {
                    container.textContent = 'Postcode Invalid';
                    return;
                }
                // other error
                container.innerHTML = `<div>Error: ${String(result.status || '')} ${String(result.statusText || '')}</div><pre>${String(result.bodyText || '')}</pre>`;
                return;
            }

            const data = result.json;

            // addresses path: show select
            if (data && Array.isArray(data.addresses)) {
                const addresses = data.addresses;
                if (addresses.length === 0) {
                    container.textContent = 'No addresses found for that postcode.';
                    return;
                }

                container.textContent = '';
                const select = document.createElement('select');
                select.id = 'addresses-select';
                const placeholder = document.createElement('option');
                placeholder.value = '';
                placeholder.textContent = '-- choose an address --';
                select.appendChild(placeholder);

                addresses.forEach((item, idx) => {
                    const opt = document.createElement('option');
                    opt.value = item.local_authority_slug || '';
                    opt.textContent = item.address || `Address ${idx + 1}`;
                    select.appendChild(opt);
                });

                select.addEventListener('change', async (ev) => {
                    const slug = ev.target.value;
                    if (!slug) return;
                    container.textContent = 'Loading authority data...';

                    const authTarget = 'https://www.gov.uk/api/local-authority/' + encodeURIComponent(slug);
                    const authUrl = 'https://api.allorigins.win/raw?url=' + encodeURIComponent(authTarget);

                    try {
                        const authResult = await fetchJsonOrDetectHtml(authUrl);
                        if (!authResult.ok) {
                            if (authResult.html || (authResult.bodyText && authResult.bodyText.trim().startsWith('<'))) {
                                container.textContent = 'Authority response invalid';
                                return;
                            }
                            container.innerHTML = `<div>Error fetching authority: ${String(authResult.status || '')} ${String(authResult.statusText || '')}</div><pre>${String(authResult.bodyText || '')}</pre>`;
                            return;
                        }

                        const authData = authResult.json;
                        if (authData && authData.local_authority) {
                            const keepName = pickDisplayNameFromLocalAuthority(authData.local_authority);
                            container.innerHTML = `<div>Kept name: <strong>${String(keepName || 'none')}</strong></div>`;
                        } else {
                            // fallback: show JSON if shape unexpected
                            container.innerHTML = `<pre>${JSON.stringify(authData, null, 2)}</pre>`;
                        }
                    } catch (err) {
                        container.textContent = 'Network error: ' + err.message;
                    }
                });

                container.appendChild(select);
                return;
            }

            // no addresses path: data may include local_authority directly
            if (data && data.local_authority) {
                const keepName = pickDisplayNameFromLocalAuthority(data.local_authority);
                container.innerHTML = `<div><strong>${String(keepName || 'none')}</strong></div>`;
                return;
            }

            // fallback: show raw JSON
            container.innerHTML = `<pre>${JSON.stringify(data, null, 2)}</pre>`;

        } catch (err) {
            container.textContent = 'Network error: ' + err.message;
        }
    });
});