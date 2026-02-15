document.addEventListener('DOMContentLoaded', () => {
    document.body.classList.remove('search-done');

    const form = document.getElementById('search-form');
    const postcodeInput = document.getElementById('postcode');
    const container = document.getElementById('address-container');
    const areaDropdown = document.getElementById('area-dropdown');
    const areaSearch = document.getElementById('area-search');

    // Store all dropdown options for filtering
    let allOptions = [];
    if (areaDropdown) {
        allOptions = Array.from(areaDropdown.options).slice(1); // Skip the placeholder
    }

    function pickDisplayNameFromLocalAuthority(localAuthority) {
        if (!localAuthority) return null;
        if (localAuthority.parent && localAuthority.parent.name) return localAuthority.parent.name;
        return localAuthority.name || null;
    }

    // normalize names for comparison (case-insensitive, collapse whitespace)
    function normalizeName(s) {
        return (s || '').toString().toLowerCase().replace(/\s+/g, ' ').trim();
    }

    function hideAllAreas() {
        document.querySelectorAll('.area').forEach(a => a.classList.remove('visible'));
    }

    function showMatches(authorityName) {
        hideAllAreas();
        if (!authorityName) return;
        const target = normalizeName(authorityName);
        if (!target) return;

        const areas = Array.from(document.querySelectorAll('.area'));
        const matched = areas.filter(area => {
            const nameEl = area.querySelector('.area-name');
            const areaName = nameEl ? normalizeName(nameEl.textContent) : '';
            return areaName === target;
        });

        if (matched.length === 0) {
            // no match - leave all hidden
            return;
        }

        matched.forEach(a => a.classList.add('visible'));
        // scroll first match into view for convenience
        try {
            matched[0].scrollIntoView({ behavior: 'smooth', block: 'center' });
            matched[0].focus?.();
        } catch (e) {
            /* ignore scroll errors */
        }
    }

    // Handle area dropdown change
    if (areaDropdown) {
        areaDropdown.addEventListener('change', (e) => {
            const selectedArea = e.target.value;
            if (selectedArea) {
                document.body.classList.add('search-done');
                container.textContent = '';
                showMatches(selectedArea);
            } else {
                hideAllAreas();
                document.body.classList.remove('search-done');
            }
        });
    }

    // Handle area search input for filtering dropdown
    if (areaSearch) {
        areaSearch.addEventListener('input', (e) => {
            const searchTerm = normalizeName(e.target.value);

            // Clear the dropdown except for the placeholder
            while (areaDropdown.options.length > 1) {
                areaDropdown.remove(1);
            }

            // Filter and re-add matching options
            const filteredOptions = allOptions.filter(option => {
                const optionText = normalizeName(option.textContent);
                return optionText.includes(searchTerm);
            });

            filteredOptions.forEach(option => {
                areaDropdown.add(option.cloneNode(true));
            });

            // If there's only one match and search term is not empty, auto-select it
            if (filteredOptions.length === 1 && searchTerm) {
                areaDropdown.selectedIndex = 1;
                areaDropdown.dispatchEvent(new Event('change'));
            }
        });

        // When clicking on the search input, show the dropdown
        areaSearch.addEventListener('focus', () => {
            areaSearch.select();
        });
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
        // not JSON according to headers- read text and try to detect HTML or parse JSON fallback
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
        hideAllAreas();

        const postcode = postcodeInput.value.trim();
        if (!postcode) {
            container.textContent = 'Please enter a postcode.';
            return;
        }

        document.body.classList.add('search-done');
        container.textContent = 'Searching...';

        const url = 'https://www.transinformed.co.uk/api/pass-thru?query=https://www.gov.uk/api/local-authority?postcode=' + encodeURIComponent(postcode);

        try {
            const result = await fetchJsonOrDetectHtml(url);

            if (!result.ok) {
                // HTML response -> Postcode Invalid
                if (result.html || (result.bodyText && result.bodyText.trim().startsWith('<'))) {
                    container.textContent = 'Postcode Invalid';
                    return;
                }
                // other error
                container.innerHTML = `<pre>Error: ${result.status} ${result.statusText}\n\n${String(result.bodyText || '')}</pre>`;
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
                    hideAllAreas();
                    if (!slug) return;

                    container.textContent = 'Loading authority data...';
                    const authUrl = 'https://www.transinformed.co.uk/api/pass-thru?query=https://www.gov.uk/api/local-authority/' + encodeURIComponent(slug);

                    try {
                        const authResult = await fetchJsonOrDetectHtml(authUrl);

                        if (!authResult.ok) {
                            if (authResult.html || (authResult.bodyText && authResult.bodyText.trim().startsWith('<'))) {
                                container.textContent = 'Authority response invalid';
                                return;
                            }
                            container.innerHTML = `<pre>Error: ${authResult.status} ${authResult.statusText}\n\n${String(authResult.bodyText || '')}</pre>`;
                            return;
                        }

                        const authData = authResult.json;
                        if (authData && authData.local_authority) {
                            const keepName = pickDisplayNameFromLocalAuthority(authData.local_authority);
                            container.innerHTML = `${keepName || 'Unknown'}`;
                            showMatches(keepName);
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
                container.innerHTML = `${keepName || 'Unknown'}`;
                showMatches(keepName);
            }
        } catch (err) {
            container.textContent = 'Network error: ' + err.message;
        }
    });

    // Copy handling for links with class .copy-link- clicking copies the displayed text
    document.addEventListener('click', (e) => {
        const link = e.target.closest && e.target.closest('.copy-link');
        if (!link) return;
        e.preventDefault();
        const value = link.getAttribute('data-copy-value') || link.textContent || '';
        if (!value) return;

        const setCopied = () => {
            const prevAria = link.getAttribute('aria-label');
            link.classList.add('copied');
            link.setAttribute('aria-label', 'Copied');
            setTimeout(() => {
                link.classList.remove('copied');
                link.setAttribute('aria-label', prevAria || 'Copy');
            }, 120);
        };

        if (navigator.clipboard && navigator.clipboard.writeText) {
            navigator.clipboard.writeText(value).then(setCopied).catch(() => {
                // fallback
                try {
                    const ta = document.createElement('textarea');
                    ta.value = value;
                    ta.style.position = 'fixed';
                    ta.style.opacity = '0';
                    document.body.appendChild(ta);
                    ta.select();
                    document.execCommand('copy');
                    document.body.removeChild(ta);
                    setCopied();
                } catch (err) {
                    console.warn('Copy failed', err);
                }
            });
        } else {
            // older fallback
            try {
                const ta = document.createElement('textarea');
                ta.value = value;
                ta.style.position = 'fixed';
                ta.style.opacity = '0';
                document.body.appendChild(ta);
                ta.select();
                document.execCommand('copy');
                document.body.removeChild(ta);
                setCopied();
            } catch (err) {
                console.warn('Copy failed', err);
            }
        }
    });
});