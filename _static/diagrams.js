(() => {
    const sizeDiagrams = () => {
        document.querySelectorAll('.md-typeset .mermaid svg').forEach((svg) => {
            const width = svg.viewBox.baseVal.width;
            if (!width || svg.dataset.nativeWidth === String(width)) return;
            svg.style.width = `${width}px`;
            svg.style.setProperty('--diagram-readable-width', `${width * 0.75}px`);
            svg.dataset.nativeWidth = String(width);
        });
    };

    // Mermaid inserts its SVG asynchronously; size it without rendering again.
    new MutationObserver(sizeDiagrams).observe(document.documentElement, {
        childList: true,
        subtree: true,
    });
    sizeDiagrams();
})();
