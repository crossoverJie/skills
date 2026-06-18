// Navigation JavaScript
document.addEventListener('DOMContentLoaded', function() {
    mermaid.initialize({
        startOnLoad: false,
        theme: 'default',
        securityLevel: 'loose',
        flowchart: { useMaxWidth: true, htmlLabels: true, curve: 'basis' },
        sequence: { useMaxWidth: true }
    });

    marked.setOptions({
        highlight: function(code, language) {
            if (language && hljs.getLanguage(language)) {
                try { return hljs.highlight(code, { language: language }).value; } catch (err) {}
            }
            try { return hljs.highlightAuto(code).value; } catch (err) { return code; }
        },
        langPrefix: 'hljs language-',
        breaks: true
    });

    showWelcomePage();
    setupNavLinks();
    setupScrollListener();
});

function showWelcomePage() {
    const contentBody = document.getElementById('content-body');
    const breadcrumb = document.getElementById('breadcrumb');
    breadcrumb.innerHTML = '<strong>首页</strong>';
    contentBody.innerHTML = `
        <div class="welcome">
            <h1>欢迎使用项目 Wiki</h1>
            <p>本文档为组内新人提供项目快速上手指南。</p>
            <div class="quick-links">
                <h3>快速导航</h3>
                <div class="link-cards">
                    <a href="#" data-file="01-system-architecture.md" class="link-card" onclick="handleCardClick(this, event)">
                        <div class="card-icon">🏗️</div>
                        <div class="card-title">系统架构</div>
                        <div class="card-desc">了解整体技术架构</div>
                    </a>
                    <a href="#" data-file="02-core-features.md" class="link-card" onclick="handleCardClick(this, event)">
                        <div class="card-icon">⭐</div>
                        <div class="card-title">核心功能</div>
                        <div class="card-desc">功能模块说明</div>
                    </a>
                    <a href="#" data-file="03-er-diagram.md" class="link-card" onclick="handleCardClick(this, event)">
                        <div class="card-icon">🗄️</div>
                        <div class="card-title">ER 图</div>
                        <div class="card-desc">数据库实体关系</div>
                    </a>
                </div>
            </div>
        </div>
    `;
}

function handleCardClick(element, event) {
    event.preventDefault();
    const file = element.getAttribute('data-file');
    if (file) {
        loadContent(file);
        updateActiveLink(element);
        if (window.innerWidth <= 1024) {
            document.querySelector('.sidebar').classList.remove('open');
        }
    }
}

function toggleSidebar() {
    document.querySelector('.sidebar').classList.toggle('open');
}

function toggleSection(element) {
    element.classList.toggle('collapsed');
    const list = element.nextElementSibling;
    if (list) list.style.display = list.style.display === 'none' ? 'block' : 'none';
}

function setupNavLinks() {
    document.querySelectorAll('.nav-list a, .link-card').forEach(link => {
        link.addEventListener('click', function(e) {
            e.preventDefault();
            const file = this.getAttribute('data-file');
            if (file) {
                loadContent(file);
                updateActiveLink(this);
                if (window.innerWidth <= 1024) {
                    document.querySelector('.sidebar').classList.remove('open');
                }
            }
        });
    });
}

function updateActiveLink(activeLink) {
    document.querySelectorAll('.nav-list a').forEach(link => link.classList.remove('active'));
    const file = activeLink.getAttribute('data-file');
    const navLink = document.querySelector(`.nav-list a[data-file="${file}"]`);
    if (navLink) navLink.classList.add('active');
}

function isFileProtocol() { return window.location.protocol === 'file:'; }

async function initMermaidDiagrams() {
    const preBlocks = document.querySelectorAll('pre');
    let mermaidCount = 0;
    preBlocks.forEach((pre, index) => {
        const codeBlock = pre.querySelector('code');
        let code = codeBlock ? (codeBlock.textContent || '') : (pre.textContent || '');
        code = code.trim();
        if (!code) return;
        const languageClass = codeBlock ? (codeBlock.className || '').toLowerCase() : '';
        const hasMermaidClass = languageClass.includes('mermaid') || languageClass.includes('language-mermaid');
        const firstLine = code.split('\n')[0].trim().toLowerCase();
        const mermaidKeywords = ['erdiagram','flowchart','sequencediagram','mindmap','graph tb','graph lr','graph rl','graph bt','graph td','graph','timeline','classdiagram','statediagram','gantt','pie','gitgraph'];
        const hasMermaidKeyword = mermaidKeywords.some(kw => firstLine.startsWith(kw));
        if (hasMermaidClass || hasMermaidKeyword) {
            mermaidCount++;
            const wrapper = document.createElement('div');
            wrapper.className = 'mermaid-wrapper';
            // 使用字符串拼接避免模板字符串中的解析问题
            wrapper.innerHTML = '<div class="mermaid-controls">' +
                '<button class="mermaid-btn zoom-in" title="放大">➕</button>' +
                '<button class="mermaid-btn zoom-out" title="缩小">➖</button>' +
                '<button class="mermaid-btn zoom-reset" title="重置">⟲</button>' +
                '<button class="mermaid-btn zoom-fullscreen" title="全屏">⛶</button>' +
            '</div>' +
            '<div class="mermaid-container">' +
                '<div class="mermaid"></div>' +
            '</div>';
            // 安全地设置 mermaid 代码
            const mermaidDiv = wrapper.querySelector('.mermaid');
            mermaidDiv.textContent = code;
            pre.replaceWith(wrapper);
        }
    });
    if (mermaidCount > 0) {
        await new Promise(r => setTimeout(r, 50));
        try { await mermaid.run({ querySelector: '.mermaid' }); } catch (e) { console.error(e); }
        setupMermaidZoom();
    }
}

function loadContent(file) {
    const contentBody = document.getElementById('content-body');
    updateBreadcrumb(file);
    if (isFileProtocol()) {
        contentBody.innerHTML = '<p>请使用 HTTP 服务器访问本 Wiki</p>';
        return;
    }
    fetch(file)
        .then(r => r.text())
        .then(async markdown => {
            contentBody.innerHTML = marked.parse(markdown);
            contentBody.querySelectorAll('a[href]').forEach(link => {
                if (link.href.startsWith('http://') || link.href.startsWith('https://')) {
                    link.setAttribute('target', '_blank');
                    link.setAttribute('rel', 'noopener noreferrer');
                }
            });
            await initMermaidDiagrams();
            window.scrollTo(0, 0);
        });
}

function updateBreadcrumb(file) {
    const breadcrumb = document.getElementById('breadcrumb');
    const filename = file.split('/').pop().replace('.md', '');
    let section = file.startsWith('service/') ? 'gRPC 接口 / ' : (file.startsWith('01-') || file.startsWith('02-') || file.startsWith('03-') ? '系统概览 / ' : '');
    breadcrumb.innerHTML = `<strong>${section}${filename}</strong>`;
}

function setupScrollListener() {
    let backToTop = document.querySelector('.back-to-top');
    if (!backToTop) {
        backToTop = document.createElement('div');
        backToTop.className = 'back-to-top';
        backToTop.innerHTML = '↑';
        backToTop.addEventListener('click', () => window.scrollTo({ top: 0, behavior: 'smooth' }));
        document.body.appendChild(backToTop);
    }
    window.addEventListener('scroll', () => {
        backToTop.classList.toggle('visible', window.pageYOffset > 300);
    });
}

function escapeHtml(text) {
    const div = document.createElement('div');
    div.textContent = text;
    return div.innerHTML;
}

function setupMermaidZoom() {
    document.querySelectorAll('.mermaid-wrapper').forEach(wrapper => {
        const container = wrapper.querySelector('.mermaid-container');
        const svg = container.querySelector('svg');
        if (!svg) return;

        let scale = 1;
        const minScale = 0.2;
        const maxScale = 5;
        const zoomStep = 0.2;

        function updateTransform() {
            svg.style.transform = 'scale(' + scale + ')';
            svg.style.transformOrigin = 'top left';
        }

        wrapper.querySelector('.zoom-in').addEventListener('click', () => {
            if (scale < maxScale) {
                scale += zoomStep;
                updateTransform();
            }
        });

        wrapper.querySelector('.zoom-out').addEventListener('click', () => {
            if (scale > minScale) {
                scale -= zoomStep;
                updateTransform();
            }
        });

        wrapper.querySelector('.zoom-reset').addEventListener('click', () => {
            scale = 1;
            updateTransform();
        });

        wrapper.querySelector('.zoom-fullscreen').addEventListener('click', () => {
            if (document.fullscreenElement) {
                document.exitFullscreen();
            } else {
                wrapper.requestFullscreen();
            }
        });

        // 鼠标滚轮缩放
        container.addEventListener('wheel', (e) => {
            if (e.ctrlKey || e.metaKey) {
                e.preventDefault();
                if (e.deltaY < 0 && scale < maxScale) {
                    scale += zoomStep;
                } else if (e.deltaY > 0 && scale > minScale) {
                    scale -= zoomStep;
                }
                updateTransform();
            }
        }, { passive: false });

        // 初始设置
        svg.style.transition = 'transform 0.2s ease';
        updateTransform();
    });
}
