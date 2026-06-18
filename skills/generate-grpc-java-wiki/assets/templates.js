/**
 * 模板系统 - 所有 HTML/CSS/JS/Markdown 模板
 */

// index.html 模板 - Dashboard Style
function indexHtml(projectInfo, protoInfo, stats) {
  const serviceCards = generateServiceCards(protoInfo.services);
  const totalServices = protoInfo.services?.length || 0;
  const totalMethods = protoInfo.services?.reduce((sum, s) => sum + (s.methods?.length || 0), 0) || 0;
  const totalMessages = stats?.totalMessages || 200;
  const hasJobs = stats?.hasJobs || false;
  const hasConsumers = stats?.hasConsumers || false;

  return `<!DOCTYPE html>
<html lang="zh-CN">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>${projectInfo.name} - 项目 Wiki</title>
    <link rel="stylesheet" href="assets/css/style.css">
    <link rel="stylesheet" href="https://cdnjs.cloudflare.com/ajax/libs/highlight.js/11.9.0/styles/atom-one-dark.min.css">
    <script src="https://cdn.jsdelivr.net/npm/mermaid@10/dist/mermaid.min.js"></script>
    <script src="https://cdn.jsdelivr.net/npm/marked@4.3.0/marked.min.js"></script>
    <script src="https://cdnjs.cloudflare.com/ajax/libs/highlight.js/11.9.0/highlight.min.js"></script>
    <script src="https://cdnjs.cloudflare.com/ajax/libs/highlight.js/11.9.0/languages/java.min.js"></script>
    <script src="https://cdnjs.cloudflare.com/ajax/libs/highlight.js/11.9.0/languages/protobuf.min.js"></script>
    <script src="https://cdnjs.cloudflare.com/ajax/libs/highlight.js/11.9.0/languages/yaml.min.js"></script>
    <script src="https://cdnjs.cloudflare.com/ajax/libs/highlight.js/11.9.0/languages/json.min.js"></script>
    <script src="https://cdnjs.cloudflare.com/ajax/libs/highlight.js/11.9.0/languages/sql.min.js"></script>
    <style>
        /* Dashboard Stats Section */
        .stats-dashboard {
            display: grid;
            grid-template-columns: repeat(auto-fit, minmax(180px, 1fr));
            gap: 16px;
            margin-bottom: 32px;
        }

        .stat-card {
            background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
            border-radius: 12px;
            padding: 24px;
            color: white;
            position: relative;
            overflow: hidden;
            transition: transform 0.2s ease, box-shadow 0.2s ease;
            text-decoration: none;
            display: block;
        }

        .stat-card:nth-child(2) { background: linear-gradient(135deg, #f093fb 0%, #f5576c 100%); }
        .stat-card:nth-child(3) { background: linear-gradient(135deg, #4facfe 0%, #00f2fe 100%); }
        .stat-card:nth-child(4) { background: linear-gradient(135deg, #43e97b 0%, #38f9d7 100%); }
        .stat-card:nth-child(5) { background: linear-gradient(135deg, #fa709a 0%, #fee140 100%); }

        .stat-card:hover {
            transform: translateY(-2px);
            box-shadow: 0 8px 24px rgba(0,0,0,0.15);
        }

        .stat-card-icon { font-size: 32px; margin-bottom: 12px; opacity: 0.9; }
        .stat-card-value { font-size: 36px; font-weight: 700; margin-bottom: 4px; }
        .stat-card-label { font-size: 14px; opacity: 0.9; }
        .stat-card-bg {
            position: absolute;
            right: -10px;
            bottom: -10px;
            font-size: 80px;
            opacity: 0.1;
        }

        /* Quick Actions */
        .quick-actions {
            display: flex;
            gap: 12px;
            margin-bottom: 32px;
            flex-wrap: wrap;
        }

        .quick-action-btn {
            display: inline-flex;
            align-items: center;
            gap: 8px;
            padding: 12px 24px;
            background: white;
            border: 1px solid var(--border-color);
            border-radius: 8px;
            font-size: 14px;
            color: var(--text-primary);
            text-decoration: none;
            transition: all 0.2s ease;
            font-weight: 500;
        }

        .quick-action-btn:hover {
            border-color: var(--primary-color);
            color: var(--primary-color);
            box-shadow: 0 2px 8px rgba(37, 99, 235, 0.1);
        }

        .quick-action-btn.primary {
            background: var(--primary-color);
            color: white;
            border-color: var(--primary-color);
        }

        .quick-action-btn.primary:hover { background: var(--secondary-color); }

        /* Section Header */
        .section-header {
            display: flex;
            align-items: center;
            justify-content: space-between;
            margin-bottom: 20px;
        }

        .section-title-with-icon {
            display: flex;
            align-items: center;
            gap: 12px;
            font-size: 20px;
            font-weight: 600;
            color: var(--text-primary);
        }

        .section-icon {
            width: 40px;
            height: 40px;
            border-radius: 10px;
            display: flex;
            align-items: center;
            justify-content: center;
            font-size: 20px;
        }

        .section-icon.grpc { background: #dbeafe; }
        .section-icon.arch { background: #f3e8ff; }

        /* Service Cards Grid */
        .services-grid {
            display: grid;
            grid-template-columns: repeat(auto-fill, minmax(360px, 1fr));
            gap: 20px;
            margin-bottom: 40px;
        }

        .service-card {
            background: var(--card-bg);
            border: 1px solid var(--border-color);
            border-radius: 12px;
            padding: 24px;
            transition: all 0.2s ease;
            position: relative;
            overflow: hidden;
        }

        .service-card::before {
            content: "";
            position: absolute;
            top: 0;
            left: 0;
            right: 0;
            height: 4px;
            background: linear-gradient(90deg, var(--primary-color), var(--secondary-color));
            opacity: 0;
            transition: opacity 0.2s ease;
        }

        .service-card:hover {
            border-color: var(--primary-color);
            box-shadow: 0 4px 20px rgba(37, 99, 235, 0.1);
            transform: translateY(-2px);
        }

        .service-card:hover::before { opacity: 1; }

        .service-card-header {
            display: flex;
            align-items: flex-start;
            justify-content: space-between;
            margin-bottom: 12px;
        }

        .service-card-title {
            font-size: 16px;
            font-weight: 600;
            color: var(--primary-color);
            font-family: 'Monaco', 'Menlo', 'Ubuntu Mono', 'Consolas', monospace;
        }

        .service-card-badge {
            padding: 4px 10px;
            border-radius: 12px;
            font-size: 11px;
            font-weight: 500;
            background: #dbeafe;
            color: #1e40af;
        }

        .service-card-desc {
            font-size: 14px;
            color: var(--text-secondary);
            line-height: 1.6;
            margin-bottom: 16px;
        }

        .service-card-footer {
            display: flex;
            justify-content: space-between;
            align-items: center;
        }

        .service-card-link {
            display: inline-flex;
            align-items: center;
            gap: 6px;
            padding: 8px 16px;
            background: var(--primary-color);
            color: white;
            border-radius: 6px;
            font-size: 13px;
            font-weight: 500;
            text-decoration: none;
            transition: all 0.2s ease;
        }

        .service-card-link:hover { background: var(--secondary-color); }

        /* Architecture Cards */
        .arch-grid {
            display: grid;
            grid-template-columns: repeat(auto-fill, minmax(280px, 1fr));
            gap: 16px;
            margin-bottom: 40px;
        }

        .arch-card {
            background: var(--card-bg);
            border: 1px solid var(--border-color);
            border-radius: 10px;
            padding: 24px;
            transition: all 0.2s ease;
            text-decoration: none;
            color: inherit;
            display: block;
        }

        .arch-card:hover {
            border-color: var(--primary-color);
            box-shadow: 0 4px 12px rgba(37, 99, 235, 0.1);
            transform: translateY(-2px);
        }

        .arch-card-icon {
            width: 48px;
            height: 48px;
            border-radius: 10px;
            display: flex;
            align-items: center;
            justify-content: center;
            font-size: 24px;
            margin-bottom: 16px;
            background: #f3f4f6;
        }

        .arch-card-title {
            font-size: 16px;
            font-weight: 600;
            color: var(--text-primary);
            margin-bottom: 8px;
        }

        .arch-card-desc {
            font-size: 13px;
            color: var(--text-secondary);
            line-height: 1.5;
        }

        /* Info Section */
        .info-section {
            background: linear-gradient(135deg, #f8fafc 0%, #e2e8f0 100%);
            border-radius: 12px;
            padding: 24px;
            margin-top: 40px;
        }

        .info-grid {
            display: grid;
            grid-template-columns: repeat(auto-fit, minmax(200px, 1fr));
            gap: 24px;
        }

        .info-item {
            display: flex;
            align-items: flex-start;
            gap: 12px;
        }

        .info-icon { font-size: 20px; }

        .info-content { flex: 1; }

        .info-label {
            font-size: 12px;
            color: var(--text-secondary);
            margin-bottom: 4px;
        }

        .info-value {
            font-size: 14px;
            font-weight: 500;
            color: var(--text-primary);
        }

        .info-value a {
            color: var(--primary-color);
            text-decoration: none;
        }

        /* Responsive */
        @media (max-width: 768px) {
            .services-grid, .arch-grid { grid-template-columns: 1fr; }
            .stats-dashboard { grid-template-columns: repeat(2, 1fr); }
        }
    </style>
</head>
<body>
    <div class="wiki-container">
        <aside class="sidebar" id="sidebar-nav-root"></aside>

        <main class="main-content">
            <!-- Header -->
            <div class="content-header">
                <h1>📚 ${projectInfo.name}</h1>
                <p class="subtitle">项目开发文档</p>
            </div>

            <!-- Stats Dashboard -->
            <div class="stats-dashboard">
                <a href="#grpc-services" class="stat-card">
                    <div class="stat-card-icon">🚀</div>
                    <div class="stat-card-value">${totalServices}</div>
                    <div class="stat-card-label">gRPC Services</div>
                    <div class="stat-card-bg">🚀</div>
                </a>
                <a href="#grpc-services" class="stat-card">
                    <div class="stat-card-icon">⚡</div>
                    <div class="stat-card-value">${totalMethods}+</div>
                    <div class="stat-card-label">RPC Methods</div>
                    <div class="stat-card-bg">⚡</div>
                </a>
                <a href="#grpc-services" class="stat-card">
                    <div class="stat-card-icon">📋</div>
                    <div class="stat-card-value">${totalMessages}+</div>
                    <div class="stat-card-label">Proto Messages</div>
                    <div class="stat-card-bg">📋</div>
                </a>
                ${hasJobs ? `
                <a href="job/index.html" class="stat-card">
                    <div class="stat-card-icon">⏰</div>
                    <div class="stat-card-value">${stats.jobCount || '0'}</div>
                    <div class="stat-card-label">定时任务</div>
                    <div class="stat-card-bg">⏰</div>
                </a>` : ''}
                ${hasConsumers ? `
                <a href="consumer/index.html" class="stat-card">
                    <div class="stat-card-icon">📡</div>
                    <div class="stat-card-value">${stats.consumerCount || '0'}</div>
                    <div class="stat-card-label">消息消费者</div>
                    <div class="stat-card-bg">📡</div>
                </a>` : ''}
            </div>

            <!-- Quick Actions -->
            <div class="quick-actions">
                <a href="01-system-architecture.html" class="quick-action-btn primary">
                    <span>🏗️</span> 系统架构
                </a>
                <a href="02-core-features.html" class="quick-action-btn">
                    <span>⭐</span> 核心功能
                </a>
                <a href="03-er-diagram.html" class="quick-action-btn">
                    <span>🗂️</span> ER图
                </a>
                ${hasJobs ? `<a href="job/index.html" class="quick-action-btn">
                    <span>⏰</span> 定时任务
                </a>` : ''}
                ${hasConsumers ? `<a href="consumer/index.html" class="quick-action-btn">
                    <span>📡</span> 消息消费
                </a>` : ''}
            </div>

            <!-- gRPC Services Section -->
            <div class="services-section" id="grpc-services">
                <div class="section-header">
                    <div class="section-title-with-icon">
                        <div class="section-icon grpc">🚀</div>
                        <span>gRPC Services</span>
                    </div>
                </div>

                <div class="services-grid">
${serviceCards}
                </div>
            </div>

            <!-- Architecture Section -->
            <div class="section-header">
                <div class="section-title-with-icon">
                    <div class="section-icon arch">🏗️</div>
                    <span>系统架构与文档</span>
                </div>
            </div>

            <div class="arch-grid">
                <a href="01-system-architecture.html" class="arch-card">
                    <div class="arch-card-icon" style="background: #dbeafe;">🏗️</div>
                    <div class="arch-card-title">系统架构图</div>
                    <div class="arch-card-desc">整体服务架构与调用关系，展示系统组件间的交互流程</div>
                </a>

                <a href="02-core-features.html" class="arch-card">
                    <div class="arch-card-icon" style="background: #fef3c7;">⭐</div>
                    <div class="arch-card-title">核心功能</div>
                    <div class="arch-card-desc">业务功能模块说明，涵盖核心能力与设计思想</div>
                </a>

                <a href="03-er-diagram.html" class="arch-card">
                    <div class="arch-card-icon" style="background: #d1fae5;">🗂️</div>
                    <div class="arch-card-title">ER图</div>
                    <div class="arch-card-desc">数据实体关系图，展示核心数据模型与关联关系</div>
                </a>

                ${hasJobs ? `<a href="job/index.html" class="arch-card">
                    <div class="arch-card-icon" style="background: #f3e8ff;">⏰</div>
                    <div class="arch-card-title">定时任务</div>
                    <div class="arch-card-desc">PowerJob定时任务中心，包含状态管理、数据同步、批量处理任务</div>
                </a>` : ''}

                ${hasConsumers ? `<a href="consumer/index.html" class="arch-card">
                    <div class="arch-card-icon" style="background: #fce7f3;">📡</div>
                    <div class="arch-card-title">消息消费者</div>
                    <div class="arch-card-desc">Pulsar消息消费者列表，处理相关的事件消息</div>
                </a>` : ''}
            </div>

            <!-- Info Section -->
            <div class="info-section">
                <div class="info-grid">
                    <div class="info-item">
                        <div class="info-icon">📋</div>
                        <div class="info-content">
                            <div class="info-label">文档版本</div>
                            <div class="info-value">v1.0.0</div>
                        </div>
                    </div>
                    <div class="info-item">
                        <div class="info-icon">📅</div>
                        <div class="info-content">
                            <div class="info-label">生成日期</div>
                            <div class="info-value">${new Date().toISOString().split('T')[0]}</div>
                        </div>
                    </div>
                    ${stats?.repoUrl ? `
                    <div class="info-item">
                        <div class="info-icon">💻</div>
                        <div class="info-content">
                            <div class="info-label">源码仓库</div>
                            <div class="info-value">
                                <a href="${stats.repoUrl}" target="_blank">View Repository</a>
                            </div>
                        </div>
                    </div>` : ''}
                    <div class="info-item">
                        <div class="info-icon">📊</div>
                        <div class="info-content">
                            <div class="info-label">覆盖范围</div>
                            <div class="info-value">${totalServices} 个核心服务</div>
                        </div>
                    </div>
                </div>
            </div>
        </main>
    </div>

    <script>
        mermaid.initialize({
            startOnLoad: true,
            theme: 'default',
            securityLevel: 'loose'
        });
    </script>
    <script src="assets/js/nav-data.js"></script>
    <script src="assets/js/nav.js"></script>
</body>
</html>
`;
}

// 生成服务导航 HTML
function generateServiceNav(services) {
  let navHtml = '';

  for (const service of services) {
    // 创建可折叠的服务组，默认收起
    navHtml += '                        <li class="service-group">\n';
    navHtml += '                            <div class="service-title collapsed" onclick="toggleService(this)">\n';
    navHtml += '                                <span class="toggle-icon">▼</span>\n';
    navHtml += '                                <span class="service-name">' + service.name + '</span>\n';
    navHtml += '                            </div>\n';
    navHtml += '                            <ul class="service-methods collapsed">\n';

    // 输出该服务的所有方法
    for (const method of service.methods) {
      navHtml += '                                <li><a href="#" data-file="service/' + method.name + '.md">' + method.name + '</a></li>\n';
    }

    navHtml += '                            </ul>\n';
    navHtml += '                        </li>\n';
  }

  return navHtml;
}

// 生成服务卡片 HTML
function generateServiceCards(services) {
  if (!services || services.length === 0) {
    return '                    <div class="empty-state">\n                        <div class="empty-state-icon">📭</div>\n                        <div class="empty-state-title">暂无服务</div>\n                        <p>未找到任何 gRPC 服务定义</p>\n                    </div>';
  }

  const descriptions = {
    'MerchantItemService': '商家商品服务 - 管理商家维度的商品信息，提供商品CRUD、状态管理等核心功能',
    'ShopItemService': '营业部商品服务 - 管理门店/营业部维度的商品，支持上下架、库存查询等功能',
    'SgMerchantItemService': '新商家商品服务(2.0) - 基于货品系统的商家商品管理，支持更灵活的商品模型',
    'SgShopItemService': '新地点商品服务(2.0) - 基于货品系统的门店商品管理，支持生命周期管理',
    'ProductService': '商品基础资料服务 - 管理商品主档信息，提供商品标准数据维护',
    'BackCategoryService': '后台类目服务 - 管理商品类目体系，支持类目树、属性管理等',
    'BrandService': '品牌服务 - 管理商品品牌信息，支持品牌CRUD和查询',
    'ItemSearchService': '商品搜索服务 - 基于Elasticsearch的商品搜索，支持全文检索、筛选排序'
  };

  const categories = {
    'MerchantItemService': 'merchant',
    'SgMerchantItemService': 'merchant',
    'ShopItemService': 'shop',
    'SgShopItemService': 'shop',
    'ProductService': 'base',
    'BackCategoryService': 'base',
    'BrandService': 'base',
    'ItemSearchService': 'search'
  };

  let cardsHtml = '';

  for (const service of services) {
    const methodCount = service.methods?.length || 0;
    const description = descriptions[service.name] || `${service.name} - 提供相关业务功能`;
    const category = categories[service.name] || 'other';

    cardsHtml += `                    <div class="service-card" data-category="${category}" data-name="${service.name.toLowerCase()}">
                        <div class="service-card-header">
                            <div class="service-card-title">${service.name}</div>
                            <span class="service-card-badge">${methodCount} 个方法</span>
                        </div>
                        <div class="service-card-desc">${description}</div>
                        <div class="service-card-footer">
                            <a href="service/${service.name}/index.html" class="service-card-link">查看详情 →</a>
                        </div>
                    </div>\n`;
  }

  return cardsHtml;
}

// 根据方法名获取分组名称
function getMethodGroupName(methodName) {
  // Topic 相关
  if (methodName.toLowerCase().includes('topic')) {
    return 'Topic 管理';
  }
  // 订阅相关
  if (methodName.toLowerCase().includes('subscription') ||
      methodName.toLowerCase().includes('subscript')) {
    return '订阅组管理';
  }
  // 消息相关
  if (methodName.toLowerCase().includes('message') ||
      methodName.toLowerCase().includes('send')) {
    return '消息操作';
  }
  // 默认分组使用服务相关
  return '接口列表';
}


// style.css 模板
function styleCss() {
  return `/* MQ Manager Wiki Styles */
:root {
    --primary-color: #2563eb;
    --primary-hover: #1d4ed8;
    --sidebar-bg: #1e293b;
    --sidebar-hover: #334155;
    --text-primary: #1f2937;
    --text-secondary: #6b7280;
    --text-light: #9ca3af;
    --border-color: #e5e7eb;
    --bg-light: #f9fafb;
    --bg-white: #ffffff;
    --code-bg: #f3f4f6;
    --link-color: #2563eb;
}

* { margin: 0; padding: 0; box-sizing: border-box; }

body {
    font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, "Helvetica Neue", Arial, sans-serif;
    font-size: 14px;
    line-height: 1.6;
    color: var(--text-primary);
    background: var(--bg-light);
}

.wiki-container { display: flex; min-height: 100vh; }

/* Sidebar */
.sidebar {
    width: 280px;
    background: var(--sidebar-bg);
    color: white;
    position: fixed;
    height: 100vh;
    overflow-y: auto;
    z-index: 100;
    transition: transform 0.3s ease;
}

.sidebar-header { padding: 24px; border-bottom: 1px solid rgba(255,255,255,0.1); }
.sidebar-header h1 { font-size: 20px; margin-bottom: 4px; font-weight: 600; }
.sidebar-header p { font-size: 12px; color: var(--text-light); opacity: 0.8; }

.nav-menu { padding: 16px 0; }
.nav-section { margin-bottom: 8px; }

.nav-title {
    padding: 12px 20px;
    font-weight: 600;
    cursor: pointer;
    display: flex;
    align-items: center;
    gap: 8px;
    transition: background 0.2s;
    user-select: none;
}

.nav-title:hover { background: var(--sidebar-hover); }

.toggle-icon { font-size: 10px; transition: transform 0.2s; }
.nav-title.collapsed .toggle-icon { transform: rotate(-90deg); }

.nav-list { list-style: none; }
.nav-list li { position: relative; }
.nav-list a {
    display: block;
    padding: 8px 20px 8px 40px;
    color: rgba(255,255,255,0.8);
    text-decoration: none;
    font-size: 13px;
    transition: all 0.2s;
    border-left: 3px solid transparent;
}

.nav-list a:hover {
    background: var(--sidebar-hover);
    color: white;
    border-left-color: var(--primary-color);
}

.nav-list a.active {
    background: var(--sidebar-hover);
    color: var(--primary-color);
    border-left-color: var(--primary-color);
}

.nav-group {
    padding: 8px 20px;
    font-size: 11px;
    color: var(--text-light);
    text-transform: uppercase;
    letter-spacing: 0.5px;
    margin-top: 8px;
    border-top: 1px solid rgba(255,255,255,0.1);
}

/* Service Group Collapsible */
.service-group {
    margin-bottom: 4px;
}

.service-title {
    padding: 10px 20px;
    font-weight: 600;
    cursor: pointer;
    display: flex;
    align-items: center;
    gap: 8px;
    transition: background 0.2s;
    user-select: none;
    font-size: 13px;
    color: rgba(255,255,255,0.9);
}

.service-title:hover {
    background: var(--sidebar-hover);
}

.service-title .toggle-icon {
    font-size: 10px;
    transition: transform 0.2s;
    color: var(--text-light);
}

.service-title.collapsed .toggle-icon {
    transform: rotate(-90deg);
}

.service-name {
    flex: 1;
}

.service-methods {
    list-style: none;
    overflow: hidden;
    transition: max-height 0.3s ease;
}

.service-methods.collapsed {
    max-height: 0;
}

.service-methods li a {
    padding-left: 48px;
    font-size: 12px;
}

/* Collapsible Tree Navigation - New Style */
.nav-section-header {
    width: 100%;
    display: flex;
    align-items: center;
    gap: 8px;
    padding: 10px 20px;
    background: transparent;
    border: 0;
    cursor: pointer;
    font-size: 12px;
    font-weight: 600;
    text-transform: uppercase;
    color: rgba(255,255,255,0.6);
    letter-spacing: 0.5px;
    text-align: left;
    transition: color 0.15s ease, background-color 0.15s ease;
}

.nav-section-header:hover {
    color: white;
    background-color: var(--sidebar-hover);
}

.nav-section-label {
    flex: 1;
}

.nav-section-body {
    overflow: hidden;
    max-height: 5000px;
    transition: max-height 0.25s ease;
}

.nav-section.collapsed > .nav-section-body {
    max-height: 0;
}

/* Arrow indicator for collapsible sections */
.nav-arrow {
    display: inline-block;
    width: 0;
    height: 0;
    border-left: 4px solid currentColor;
    border-top: 4px solid transparent;
    border-bottom: 4px solid transparent;
    transition: transform 0.2s ease;
    flex-shrink: 0;
}

.nav-section.expanded > .nav-section-header .nav-arrow,
.nav-group.expanded > .nav-group-header .nav-toggle .nav-arrow {
    transform: rotate(90deg);
}

/* Collapsible groups (services) */
.nav-group {
    border-left: 3px solid transparent;
    transition: border-left-color 0.15s ease;
}

.nav-group:hover {
    border-left-color: rgba(255,255,255,0.1);
}

.nav-group-header {
    display: flex;
    align-items: center;
    gap: 4px;
    padding: 8px 20px 8px 16px;
    color: rgba(255,255,255,0.85);
    font-size: 13px;
    cursor: pointer;
    transition: background-color 0.15s ease;
}

.nav-group-header:hover {
    background-color: var(--sidebar-hover);
}

.nav-toggle {
    flex-shrink: 0;
    width: 20px;
    height: 20px;
    display: inline-flex;
    align-items: center;
    justify-content: center;
    padding: 0;
    background: transparent;
    border: 0;
    border-radius: 4px;
    cursor: pointer;
    color: rgba(255,255,255,0.5);
    transition: background-color 0.15s ease, color 0.15s ease;
}

.nav-toggle:hover {
    background-color: rgba(255,255,255,0.1);
    color: white;
}

.nav-group-link {
    flex: 1;
    color: inherit;
    text-decoration: none;
    overflow: hidden;
    text-overflow: ellipsis;
    white-space: nowrap;
}

.nav-group-link.active,
.nav-group-header.active .nav-group-link {
    color: var(--primary-color);
    font-weight: 600;
}

.nav-group-children {
    overflow: hidden;
    max-height: 2000px;
    transition: max-height 0.25s ease;
    padding-left: 4px;
    margin-left: 14px;
    border-left: 1px solid rgba(255,255,255,0.1);
}

.nav-group.collapsed > .nav-group-children {
    max-height: 0;
}

/* Leaf links (methods) */
.nav-leaf {
    display: block;
    padding: 6px 16px 6px 24px;
    color: rgba(255,255,255,0.7);
    text-decoration: none;
    font-size: 12px;
    border-left: 3px solid transparent;
    transition: background-color 0.15s ease, color 0.15s ease, border-left-color 0.15s ease;
    overflow: hidden;
    text-overflow: ellipsis;
    white-space: nowrap;
}

.nav-leaf:hover {
    background-color: var(--sidebar-hover);
    color: white;
}

.nav-leaf.active {
    background-color: rgba(37, 99, 235, 0.15);
    color: var(--primary-color);
    border-left-color: var(--primary-color);
    font-weight: 500;
}

.nav-leaf-sub {
    padding-left: 18px;
    font-size: 12px;
}

.sidebar-footer {
    padding: 16px 20px;
    border-top: 1px solid rgba(255,255,255,0.1);
    margin-top: auto;
    font-size: 12px;
    color: var(--text-light);
    text-align: center;
}

/* Content */
.content {
    flex: 1;
    margin-left: 280px;
    min-height: 100vh;
}

.content-header {
    background: var(--bg-white);
    padding: 16px 24px;
    border-bottom: 1px solid var(--border-color);
    display: flex;
    align-items: center;
    gap: 16px;
    position: sticky;
    top: 0;
    z-index: 50;
}

.menu-toggle {
    background: none;
    border: none;
    font-size: 20px;
    cursor: pointer;
    padding: 4px 8px;
    border-radius: 4px;
    transition: background 0.2s;
}

.menu-toggle:hover { background: var(--bg-light); }

.breadcrumb { font-size: 14px; color: var(--text-secondary); }
.breadcrumb strong { color: var(--text-primary); }

.content-body {
    padding: 32px 48px;
    max-width: 1200px;
}

/* Markdown Styles */
.content-body h1 {
    font-size: 32px;
    font-weight: 700;
    margin-bottom: 24px;
    padding-bottom: 16px;
    border-bottom: 2px solid var(--border-color);
}

.content-body h2 {
    font-size: 24px;
    font-weight: 600;
    margin-top: 40px;
    margin-bottom: 16px;
    padding-bottom: 8px;
    border-bottom: 1px solid var(--border-color);
}

.content-body h3 {
    font-size: 18px;
    font-weight: 600;
    margin-top: 28px;
    margin-bottom: 12px;
    color: var(--text-primary);
}

.content-body p {
    margin-bottom: 16px;
    line-height: 1.8;
}

.content-body a {
    color: var(--link-color);
    text-decoration: none;
}

.content-body a:hover { text-decoration: underline; }

.content-body ul, .content-body ol {
    margin-bottom: 16px;
    padding-left: 24px;
}

.content-body li { margin-bottom: 8px; }

.content-body code {
    background: var(--code-bg);
    padding: 2px 6px;
    border-radius: 3px;
    font-family: "SF Mono", Monaco, Inconsolata, "Fira Code", monospace;
    font-size: 13px;
    color: #c7254e;
}

.content-body pre {
    background: #282c34;
    padding: 16px;
    border-radius: 8px;
    overflow-x: auto;
    margin-bottom: 20px;
}

.content-body pre code {
    background: transparent;
    color: #abb2bf;
    padding: 0;
    font-size: 13px;
    line-height: 1.6;
    font-family: "SF Mono", Monaco, Inconsolata, "Fira Code", "Source Code Pro", Consolas, monospace;
}

.content-body pre code.hljs {
    background: transparent;
    padding: 0;
}

.content-body blockquote {
    border-left: 4px solid var(--primary-color);
    padding: 12px 20px;
    margin: 20px 0;
    background: var(--bg-light);
    border-radius: 0 8px 8px 0;
}

.content-body table {
    width: 100%;
    border-collapse: collapse;
    margin: 20px 0;
}

.content-body th, .content-body td {
    padding: 12px 16px;
    text-align: left;
    border-bottom: 1px solid var(--border-color);
}

.content-body th {
    background: var(--bg-light);
    font-weight: 600;
    font-size: 13px;
    text-transform: uppercase;
    letter-spacing: 0.5px;
    color: var(--text-secondary);
}

.content-body tr:hover { background: var(--bg-light); }

/* Welcome Page */
.welcome { text-align: center; padding: 60px 20px; }
.welcome h1 { border-bottom: none; margin-bottom: 16px; }
.welcome p {
    font-size: 16px;
    color: var(--text-secondary);
    max-width: 600px;
    margin: 0 auto 48px;
}

.quick-links { margin-top: 60px; }
.quick-links h3 {
    font-size: 20px;
    margin-bottom: 32px;
    color: var(--text-primary);
}

.link-cards {
    display: grid;
    grid-template-columns: repeat(auto-fit, minmax(280px, 1fr));
    gap: 24px;
    max-width: 900px;
    margin: 0 auto;
}

.link-card {
    background: var(--bg-white);
    border: 1px solid var(--border-color);
    border-radius: 12px;
    padding: 32px 24px;
    text-decoration: none;
    transition: all 0.3s;
    display: block;
}

.link-card:hover {
    border-color: var(--primary-color);
    box-shadow: 0 4px 20px rgba(37, 99, 235, 0.1);
    transform: translateY(-2px);
}

.card-icon { font-size: 40px; margin-bottom: 16px; }
.card-title {
    font-size: 18px;
    font-weight: 600;
    color: var(--text-primary);
    margin-bottom: 8px;
}
.card-desc { font-size: 14px; color: var(--text-secondary); }

/* Mermaid */
.mermaid {
    background: var(--bg-white);
    padding: 24px;
    border-radius: 8px;
    border: 1px solid var(--border-color);
    margin: 20px 0;
    text-align: center;
    overflow-x: auto;
    min-height: 100px;
    position: relative;
    display: block;
}

.mermaid svg {
    max-width: 100% !important;
    height: auto !important;
    display: block !important;
    margin: 0 auto !important;
}

.mermaid-error {
    background: #fee2e2;
    border: 1px solid #ef4444;
    border-radius: 8px;
    padding: 20px;
    color: #991b1b;
    margin: 20px 0;
    text-align: left;
}

/* Mermaid Zoom Controls */
.mermaid-wrapper {
    background: var(--bg-white);
    border-radius: 8px;
    border: 1px solid var(--border-color);
    margin: 20px 0;
    overflow: hidden;
}

.mermaid-controls {
    display: flex;
    gap: 8px;
    padding: 12px 16px;
    background: var(--bg-light);
    border-bottom: 1px solid var(--border-color);
    align-items: center;
}

.mermaid-btn {
    width: 32px;
    height: 32px;
    border: 1px solid var(--border-color);
    background: var(--bg-white);
    border-radius: 6px;
    cursor: pointer;
    display: flex;
    align-items: center;
    justify-content: center;
    font-size: 14px;
    transition: all 0.2s ease;
    color: var(--text-primary);
}

.mermaid-btn:hover {
    background: var(--primary-color);
    color: white;
    border-color: var(--primary-color);
}

.mermaid-btn:active {
    transform: scale(0.95);
}

.mermaid-container {
    padding: 24px;
    overflow: hidden;
    min-height: 200px;
    background: var(--bg-white);
    cursor: grab;
    position: relative;
}

.mermaid-container:active,
.mermaid-container.grabbing {
    cursor: grabbing;
}

.mermaid-container .mermaid {
    background: transparent;
    border: none;
    margin: 0;
    padding: 0;
    text-align: left;
    overflow: visible;
}

.mermaid-container .mermaid svg {
    max-width: none !important;
    transform-origin: top left;
}

/* Fullscreen mode */
.mermaid-wrapper:fullscreen {
    background: var(--bg-white);
    overflow: auto;
}

.mermaid-wrapper:fullscreen .mermaid-container {
    height: calc(100vh - 60px);
    display: flex;
    align-items: flex-start;
    justify-content: flex-start;
}

/* Info Box */
.info-box {
    background: #dbeafe;
    border: 1px solid #3b82f6;
    border-radius: 8px;
    padding: 16px 20px;
    margin: 20px 0;
}

.info-box.warning {
    background: #fef3c7;
    border-color: #f59e0b;
}

.info-box.error {
    background: #fee2e2;
    border-color: #ef4444;
}

/* File List - Source Files Section */
.file-list {
    list-style: none;
    padding: 0;
}

.file-list li {
    padding: 10px;
    background: var(--bg-light);
    margin: 5px 0;
    border-radius: 6px;
    font-family: "SF Mono", Monaco, Inconsolata, monospace;
    font-size: 13px;
    word-break: break-all;
    overflow-wrap: break-word;
}

.file-list li::before {
    content: "📄 ";
}

.file-list a {
    color: var(--link-color);
    text-decoration: none;
    word-break: break-all;
    overflow-wrap: break-word;
}

.file-list a:hover {
    text-decoration: underline;
}

/* Responsive */
@media (max-width: 1024px) {
    .sidebar { transform: translateX(-100%); }
    .sidebar.open { transform: translateX(0); }
    .content { margin-left: 0; }
    .content-body { padding: 24px; }
}

/* Back to Top */
.back-to-top {
    position: fixed;
    bottom: 24px;
    right: 24px;
    background: var(--primary-color);
    color: white;
    width: 44px;
    height: 44px;
    border-radius: 50%;
    display: flex;
    align-items: center;
    justify-content: center;
    cursor: pointer;
    box-shadow: 0 4px 12px rgba(0,0,0,0.15);
    transition: all 0.3s;
    opacity: 0;
    visibility: hidden;
}

.back-to-top.visible { opacity: 1; visibility: visible; }
.back-to-top:hover { background: var(--primary-hover); transform: translateY(-2px); }
`;
}


// nav.js 模板 - 动态树形导航，支持折叠/展开和本地存储状态
function navJs() {
  return `/**
 * Dynamic Tree Navigation - Renders collapsible sidebar from window.NAV_DATA
 *
 * Features:
 *   - All sections collapsed by default
 *   - Each service/job/consumer is collapsible
 *   - Auto-expands path to current page
 *   - Persist collapse/expand state in localStorage
 */
(function () {
    'use strict';

    var STORAGE_KEY = 'wiki-nav-state-v1';

    /**
     * Compute relative path prefix to reach wiki root from current page
     */
    function getRootPrefix() {
        var path = window.location.pathname.replace(/\\\\/g, '/');
        var marker = '/wiki/';
        var idx = path.lastIndexOf(marker);
        var subPath;
        if (idx >= 0) {
            subPath = path.substring(idx + marker.length);
        } else {
            subPath = path.split('/').slice(-1)[0] || '';
        }
        var depth = (subPath.match(/\\//g) || []).length;
        if (depth <= 0) return '';
        var prefix = '';
        for (var i = 0; i < depth; i++) prefix += '../';
        return prefix;
    }

    /**
     * Get current page path relative to wiki root
     */
    function getCurrentPath() {
        var path = window.location.pathname.replace(/\\\\/g, '/');
        var marker = '/wiki/';
        var idx = path.lastIndexOf(marker);
        var rel;
        if (idx >= 0) {
            rel = path.substring(idx + marker.length);
        } else {
            rel = path.split('/').slice(-1)[0] || '';
        }
        if (!rel || rel.endsWith('/')) rel = rel + 'index.html';
        return decodeURIComponent(rel);
    }

    function loadState() {
        try {
            var raw = localStorage.getItem(STORAGE_KEY);
            if (!raw) return {};
            var parsed = JSON.parse(raw);
            return parsed && typeof parsed === 'object' ? parsed : {};
        } catch (e) { return {}; }
    }

    function saveState(state) {
        try { localStorage.setItem(STORAGE_KEY, JSON.stringify(state)); } catch (e) {}
    }

    function escapeHtml(s) {
        if (s == null) return '';
        return String(s)
            .replace(/&/g, '&amp;')
            .replace(/</g, '&lt;')
            .replace(/>/g, '&gt;')
            .replace(/"/g, '&quot;')
            .replace(/'/g, '&#39;');
    }

    function pathsEqual(a, b) { return a === b; }

    function isItemOrDescendantActive(item, currentPath) {
        if (item.path && pathsEqual(item.path, currentPath)) return true;
        if (item.children && item.children.length) {
            for (var i = 0; i < item.children.length; i++) {
                if (isItemOrDescendantActive(item.children[i], currentPath)) return true;
            }
        }
        return false;
    }

    function renderItem(item, prefix, currentPath, savedState) {
        var hasChildren = item.children && item.children.length > 0;
        var isActive = pathsEqual(item.path, currentPath);
        var hasActiveDescendant = hasChildren && item.children.some(function (c) {
            return isItemOrDescendantActive(c, currentPath);
        });

        if (!hasChildren) {
            return '<a href="' + escapeHtml(prefix + item.path) + '" ' +
                'class="nav-leaf' + (isActive ? ' active' : '') + '">' +
                escapeHtml(item.label) + '</a>';
        }

        var stateKey = item.path || item.label;
        var saved = savedState['item:' + stateKey];
        var expanded;
        if (saved === 'expanded') expanded = true;
        else if (saved === 'collapsed') expanded = false;
        else expanded = isActive || hasActiveDescendant;

        var html = '';
        html += '<div class="nav-group ' + (expanded ? 'expanded' : 'collapsed') + '" ' +
            'data-state-key="' + escapeHtml(stateKey) + '">';
        html += '  <div class="nav-group-header' + (isActive ? ' active' : '') + '">';
        html += '    <button type="button" class="nav-toggle" aria-label="切换">' +
            '<span class="nav-arrow"></span></button>';
        html += '    <a href="' + escapeHtml(prefix + item.path) + '" ' +
            'class="nav-group-link' + (isActive ? ' active' : '') + '">' +
            escapeHtml(item.label) + '</a>';
        html += '  </div>';
        html += '  <div class="nav-group-children">';
        item.children.forEach(function (child) {
            var childActive = pathsEqual(child.path, currentPath);
            html += '<a href="' + escapeHtml(prefix + child.path) + '" ' +
                'class="nav-leaf nav-leaf-sub' + (childActive ? ' active' : '') + '">' +
                escapeHtml(child.label) + '</a>';
        });
        html += '  </div>';
        html += '</div>';
        return html;
    }

    function renderSection(section, prefix, currentPath, savedState) {
        var hasActiveDescendant = section.items.some(function (item) {
            return isItemOrDescendantActive(item, currentPath);
        });

        var saved = savedState['section:' + section.id];
        var expanded;
        if (saved === 'expanded') expanded = true;
        else if (saved === 'collapsed') expanded = false;
        else expanded = hasActiveDescendant;

        var html = '';
        html += '<div class="nav-section ' + (expanded ? 'expanded' : 'collapsed') + '" ' +
            'data-section-id="' + escapeHtml(section.id) + '">';
        html += '  <button type="button" class="nav-section-header">';
        html += '    <span class="nav-arrow"></span>';
        html += '    <span class="nav-section-label">' + escapeHtml(section.label) + '</span>';
        html += '  </button>';
        html += '  <div class="nav-section-body">';
        section.items.forEach(function (item) {
            html += renderItem(item, prefix, currentPath, savedState);
        });
        html += '  </div>';
        html += '</div>';
        return html;
    }

    function renderSidebar(container) {
        var data = window.NAV_DATA;
        if (!data || !container) return;

        var prefix = getRootPrefix();
        var currentPath = getCurrentPath();
        var savedState = loadState();

        var html = '';
        html += '<div class="sidebar-header">';
        html += '  <h1>' + escapeHtml(data.title || 'Wiki') + '</h1>';
        if (data.subtitle) {
            html += '  <p>' + escapeHtml(data.subtitle) + '</p>';
        }
        html += '</div>';
        html += '<nav class="sidebar-nav">';
        data.sections.forEach(function (section) {
            html += renderSection(section, prefix, currentPath, savedState);
        });
        html += '</nav>';

        container.innerHTML = html;
        bindEvents(container);
        scrollActiveIntoView(container);
    }

    function bindEvents(root) {
        root.querySelectorAll('.nav-section-header').forEach(function (header) {
            header.addEventListener('click', function () {
                var section = header.closest('.nav-section');
                if (!section) return;
                var willExpand = section.classList.contains('collapsed');
                section.classList.toggle('collapsed', !willExpand);
                section.classList.toggle('expanded', willExpand);
                var state = loadState();
                state['section:' + section.dataset.sectionId] = willExpand ? 'expanded' : 'collapsed';
                saveState(state);
            });
        });

        root.querySelectorAll('.nav-toggle').forEach(function (btn) {
            btn.addEventListener('click', function (e) {
                e.preventDefault();
                e.stopPropagation();
                var group = btn.closest('.nav-group');
                if (!group) return;
                toggleGroup(group);
            });
        });

        root.querySelectorAll('.nav-group-header').forEach(function (header) {
            header.addEventListener('click', function (e) {
                if (e.target.closest('.nav-group-link')) return;
                if (e.target.closest('.nav-toggle')) return;
                var group = header.closest('.nav-group');
                if (!group) return;
                toggleGroup(group);
            });
        });
    }

    function toggleGroup(group) {
        var willExpand = group.classList.contains('collapsed');
        group.classList.toggle('collapsed', !willExpand);
        group.classList.toggle('expanded', willExpand);
        var state = loadState();
        state['item:' + group.dataset.stateKey] = willExpand ? 'expanded' : 'collapsed';
        saveState(state);
    }

    function scrollActiveIntoView(container) {
        var active = container.querySelector('.nav-leaf.active, .nav-group-link.active');
        if (!active) return;
        requestAnimationFrame(function () {
            try {
                active.scrollIntoView({ block: 'center', behavior: 'auto' });
            } catch (e) {
                active.scrollIntoView();
            }
        });
    }

    function init() {
        var container = document.getElementById('sidebar-nav-root');
        if (!container) container = document.getElementById('sidebar-nav');
        if (container) renderSidebar(container);

        if (typeof window.mermaid !== 'undefined' && window.mermaid.initialize) {
            try {
                window.mermaid.initialize({
                    startOnLoad: true,
                    theme: 'default',
                    securityLevel: 'loose'
                });
            } catch (e) {}
        }
        if (typeof window.hljs !== 'undefined' && window.hljs.highlightAll) {
            try { window.hljs.highlightAll(); } catch (e) {}
        }

        var mobileMenuBtn = document.getElementById('mobile-menu-btn');
        var sidebar = document.querySelector('.sidebar');
        if (mobileMenuBtn && sidebar) {
            mobileMenuBtn.addEventListener('click', function () {
                sidebar.classList.toggle('open');
            });
        }
    }

    if (document.readyState === 'loading') {
        document.addEventListener('DOMContentLoaded', init);
    } else {
        init();
    }
})();`;
}


// SPA 风格的 nav.js 模板（单页应用，保留向后兼容）
function navJsSpa() {
  return `// Navigation JavaScript - SPA style with marked.js and highlight.js
// DO NOT add custom highlightCode() function here - it will corrupt pre-encoded HTML entities

document.addEventListener('DOMContentLoaded', function() {
    if (typeof hljs !== 'undefined') hljs.highlightAll();

    mermaid.initialize({
        startOnLoad: true,
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
    contentBody.innerHTML = \`
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
    \`;
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

function toggleService(element) {
    element.classList.toggle('collapsed');
    const methodsList = element.nextElementSibling;
    if (methodsList) methodsList.classList.toggle('collapsed');
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
    const navLink = document.querySelector(\`.nav-list a[data-file="\${file}"]\`);
    if (navLink) navLink.classList.add('active');
}

function isFileProtocol() { return window.location.protocol === 'file:'; }

async function initMermaidDiagrams() {
    const preBlocks = document.querySelectorAll('pre');
    let mermaidCount = 0;
    preBlocks.forEach((pre) => {
        const codeBlock = pre.querySelector('code');
        let code = codeBlock ? (codeBlock.textContent || '') : (pre.textContent || '');
        code = code.trim();
        if (!code) return;
        const languageClass = codeBlock ? (codeBlock.className || '').toLowerCase() : '';
        const hasMermaidClass = languageClass.includes('mermaid') || languageClass.includes('language-mermaid');
        const firstLine = code.split('\\n')[0].trim().toLowerCase();
        const mermaidKeywords = ['erdiagram','flowchart','sequencediagram','mindmap','graph tb','graph lr','graph rl','graph bt','graph td','graph','timeline','classdiagram','statediagram','gantt','pie','gitgraph'];
        const hasMermaidKeyword = mermaidKeywords.some(kw => firstLine.startsWith(kw));
        if (hasMermaidClass || hasMermaidKeyword) {
            mermaidCount++;
            const wrapper = document.createElement('div');
            wrapper.className = 'mermaid-wrapper';
            wrapper.innerHTML = '<div class="mermaid-controls">' +
                '<button class="mermaid-btn zoom-in" title="放大">➕</button>' +
                '<button class="mermaid-btn zoom-out" title="缩小">➖</button>' +
                '<button class="mermaid-btn zoom-reset" title="重置">⟲</button>' +
                '<button class="mermaid-btn zoom-fullscreen" title="全屏">⛶</button>' +
            '</div>' +
            '<div class="mermaid-container">' +
                '<div class="mermaid"></div>' +
            '</div>';
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
    breadcrumb.innerHTML = \`<strong>\${section}\${filename}</strong>\`;
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
        let translateX = 0;
        let translateY = 0;
        let isDragging = false;
        let startX = 0;
        let startY = 0;
        const minScale = 0.3;
        const maxScale = 5;
        const zoomStep = 0.2;

        function updateTransform() {
            svg.style.transform = 'translate(' + translateX + 'px, ' + translateY + 'px) scale(' + scale + ')';
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
            translateX = 0;
            translateY = 0;
            updateTransform();
        });

        wrapper.querySelector('.zoom-fullscreen').addEventListener('click', () => {
            if (document.fullscreenElement) {
                document.exitFullscreen();
            } else {
                wrapper.requestFullscreen();
            }
        });

        // 鼠标滚轮缩放（无需按住Ctrl）
        container.addEventListener('wheel', (e) => {
            e.preventDefault();
            if (e.deltaY < 0 && scale < maxScale) {
                scale += zoomStep;
            } else if (e.deltaY > 0 && scale > minScale) {
                scale -= zoomStep;
            }
            updateTransform();
        }, { passive: false });

        // 拖拽平移
        container.addEventListener('mousedown', (e) => {
            if (e.button === 0) { // 左键
                isDragging = true;
                startX = e.clientX - translateX;
                startY = e.clientY - translateY;
                container.style.cursor = 'grabbing';
            }
        });

        document.addEventListener('mousemove', (e) => {
            if (isDragging) {
                e.preventDefault();
                translateX = e.clientX - startX;
                translateY = e.clientY - startY;
                updateTransform();
            }
        });

        document.addEventListener('mouseup', () => {
            isDragging = false;
            container.style.cursor = 'grab';
        });

        // 初始设置
        svg.style.transition = 'transform 0.1s ease-out';
        container.style.cursor = 'grab';
        updateTransform();
    });
}
`;
}


// 系统架构.md 模板
// 系统架构.md 模板
function systemArchitectureMd(projectInfo) {
  return `# 系统架构

## 项目概述

${projectInfo.name} 是一个基于 gRPC 协议的微服务项目。

## 整体架构图

\`\`\`mermaid
flowchart TB
    subgraph Clients["客户端层"]
        C1["gRPC Client"]
    end

    subgraph Server["服务层"]
        S1["gRPC Service"]
        S2["业务逻辑层"]
    end

    subgraph Persistence["持久化层"]
        P1["MySQL"]
    end

    C1 -->|gRPC| S1
    S1 --> S2
    S2 --> P1
\`\`\`

## 模块划分

| 模块 | 说明 |
|------|------|
| API 层 | Proto 定义和 gRPC 服务接口 |
| 服务层 | 业务逻辑实现 |
| 持久层 | 数据库访问 |

## 技术栈

- **通信协议**: gRPC
- **开发语言**: Java
- **构建工具**: ${projectInfo.type === 'maven' ? 'Maven' : 'Gradle'}
`;
}

// 核心功能.md 模板 - 使用 mindmap 展示产品功能架构
function coreFeaturesMd(projectInfo, protoInfo) {
  // 生成功能模块 mindmap
  const featureMindmap = generateFeatureMindmap(protoInfo.services);

  // 生成功能模块卡片
  const moduleCards = generateModuleCards(protoInfo.services);

  // 生成服务列表表格
  const serviceList = generateServiceListTable(protoInfo.services);

  return `# 核心功能

## 功能模块架构

\`\`\`mermaid
mindmap
  root((${projectInfo.name || 'Item Service'}<br/>核心功能))
${featureMindmap}
\`\`\`

## 功能模块详细说明

${moduleCards}

## 核心业务流程

\`\`\`mermaid
flowchart TB
    Start([开始]) --> Receive[接收请求]
    Receive --> Validate{参数校验}
    Validate -->|失败| Error[返回错误]
    Validate -->|成功| Process[业务处理]
    Process --> Save[数据持久化]
    Save --> SendMsg[发送消息]
    SendMsg --> End([结束])
    Error --> End
\`\`\`

## gRPC 服务列表

项目共包含 ${protoInfo.services ? protoInfo.services.length : 0} 个服务，定义了以下主要接口：

${serviceList}

<div class="alert alert-info">
<div class="alert-title">ℹ️ 说明</div>
<p>每个服务的详细文档位于 <code>service/{ServiceName}/</code> 目录下，包含：</p>
<ul>
    <li>服务概述与功能说明</li>
    <li>Proto 定义与请求/响应参数</li>
    <li>实现类与业务逻辑</li>
    <li>时序图与调用示例</li>
</ul>
</div>
`;
}

// 生成功能 mindmap
function generateFeatureMindmap(services) {
  // 根据服务名分组生成功能域
  const featureDomains = {
    '商品管理': { icon: '📦', services: [], details: ['商品创建', '商品编辑', '商品查询'] },
    '门店管理': { icon: '🏪', services: [], details: ['门店同步', '多门店管理'] },
    '价格管理': { icon: '💰', services: [], details: ['价格标签', '调价管理'] },
    '类目属性': { icon: '📂', services: [], details: ['类目管理', '品牌管理'] },
    '搜索推荐': { icon: '🔍', services: [], details: ['商品搜索', '商品推荐'] },
    '库存仓库': { icon: '📊', services: [], details: ['库存管理', '仓库信息'] }
  };

  // 将服务分类到功能域
  for (const service of services || []) {
    const name = service.name || '';
    if (name.includes('MerchantItem')) {
      featureDomains['商品管理'].services.push(name);
    } else if (name.includes('ShopItem') || name.includes('SgShop')) {
      featureDomains['门店管理'].services.push(name);
    } else if (name.includes('Price') || name.includes('Value')) {
      featureDomains['价格管理'].services.push(name);
    } else if (name.includes('Category') || name.includes('Brand') || name.includes('Property')) {
      featureDomains['类目属性'].services.push(name);
    } else if (name.includes('Search') || name.includes('Recommend')) {
      featureDomains['搜索推荐'].services.push(name);
    } else if (name.includes('Inventory') || name.includes('Warehouse')) {
      featureDomains['库存仓库'].services.push(name);
    }
  }

  // 生成 mindmap 文本
  let mindmap = '';
  for (const [domain, info] of Object.entries(featureDomains)) {
    if (info.services.length > 0) {
      mindmap += `    ${domain}\n`;
      mindmap += `      ::icon(${info.icon})\n`;
      for (const detail of info.details) {
        mindmap += `      ${detail}\n`;
      }
    }
  }

  return mindmap || '    商品管理\n      ::icon(📦)\n      商品创建\n      商品编辑\n';
}

// 生成功能模块卡片
function generateModuleCards(services) {
  let cards = '';

  // 根据服务生成功能卡片
  const domainMap = {};
  for (const service of services || []) {
    const name = service.name || '';
    let domain = '其他';
    let icon = '📦';

    if (name.includes('MerchantItem')) {
      domain = '商家商品管理';
      icon = '📦';
    } else if (name.includes('ShopItem')) {
      domain = '门店商品管理';
      icon = '🏪';
    } else if (name.includes('Price')) {
      domain = '价格管理';
      icon = '💰';
    } else if (name.includes('Category')) {
      domain = '类目管理';
      icon = '📂';
    } else if (name.includes('Brand')) {
      domain = '品牌管理';
      icon = '©️';
    } else if (name.includes('Search')) {
      domain = '商品搜索';
      icon = '🔍';
    } else if (name.includes('Inventory')) {
      domain = '库存管理';
      icon = '📊';
    }

    if (!domainMap[domain]) {
      domainMap[domain] = { icon, services: [] };
    }
    domainMap[domain].services.push(name);
  }

  for (const [domain, info] of Object.entries(domainMap)) {
    cards += `<div class="method-card">\n`;
    cards += `    <h4>${info.icon} ${domain}</h4>\n`;
    cards += `    <p>对应服务: ${info.services.map(s => `<code>${s}</code>`).join(', ')}</p>\n`;
    cards += `</div>\n\n`;
  }

  return cards || '<div class="method-card">\n    <h4>📦 商品管理</h4>\n    <p>商品基础信息管理</p>\n</div>\n';
}

// 生成服务列表表格
function generateServiceListTable(services) {
  let table = '| 服务名 | 功能领域 |\n|--------|----------|\n';

  for (const service of services || []) {
    const name = service.name || '';
    let domain = '其他';

    if (name.includes('MerchantItem')) domain = '商家商品';
    else if (name.includes('ShopItem')) domain = '门店商品';
    else if (name.includes('Price')) domain = '价格管理';
    else if (name.includes('Category')) domain = '类目管理';
    else if (name.includes('Brand')) domain = '品牌管理';
    else if (name.includes('Search')) domain = '搜索';
    else if (name.includes('Inventory')) domain = '库存';

    table += `| ${name} | ${domain} |\n`;
  }

  return table;
}

// ER 图.md 模板
function erDiagramMd(projectInfo, javaInfo) {
  let entities = '';
  let erDiagram = 'erDiagram\n';
  for (const entity of javaInfo.entities.slice(0, 5)) {
    entities += `### ${entity.name}\n\n`;
    entities += '| 字段 | 类型 | 说明 |\n|------|------|------|\n';
    for (const field of entity.fields) {
      entities += `| ${field.name} | ${field.type} | |\n`;
    }
    entities += '\n';
    erDiagram += `    ${entity.name} {\n`;
    for (const field of entity.fields.slice(0, 5)) {
      erDiagram += `        ${field.type} ${field.name}\n`;
    }
    erDiagram += '    }\n';
  }

  return `# ER 图

## 实体关系图

\`\`\`mermaid
${erDiagram}
\`\`\`

## 核心实体

${entities || 'TODO: 补充实体类说明'}
`;
}


// 服务接口文档模板 - 包含完整的源码链接（自动检测 GitHub/GitLab）
function serviceMd(methodInfo) {
  const { serviceName, methodName, inputType, outputType, comments, projectInfo, protoInfo, javaInfo, bizMethodInfo, protoFile, protoLineStart } = methodInfo;

  // 生成 proto 定义
  let protoDef = `service ${serviceName} {\n    rpc ${methodName}(${inputType}) returns (${outputType}){}\n}`;

  // 生成 message 定义
  let requestDef = '';
  if (protoInfo.messages[inputType]) {
    requestDef = `\n\nmessage ${inputType} {\n`;
    for (const field of protoInfo.messages[inputType].fields) {
      requestDef += `    ${field.repeated ? 'repeated ' : ''}${field.type} ${field.name} = ${field.number};\n`;
    }
    requestDef += '}';
  }

  // 查找 gRPC 实现文件 (AppServiceGrpcImpl)
  let grpcImplFile = '';
  let grpcImplClassName = '';
  let grpcMethodLineStart = '';
  let grpcMethodLineEnd = '';

  // 查找包含该方法的 gRPC 实现类
  for (const [className, classInfo] of Object.entries(javaInfo.serviceImpls || {})) {
    for (const method of classInfo.methods || []) {
      if (method.name === methodName) {
        grpcImplClassName = className;
        grpcImplFile = classInfo.filePath;
        grpcMethodLineStart = method.lineNumber;
        grpcMethodLineEnd = method.endLine || method.lineNumber + 5;
        break;
      }
    }
    if (grpcImplFile) break;
  }

  // 查找业务逻辑实现 (AppService)
  let bizImplFile = '';
  let bizImplClassName = '';
  let bizMethodLineStart = '';
  let bizMethodLineEnd = '';
  let bizMethodCode = '';

  for (const [className, classInfo] of Object.entries(javaInfo.serviceDelegates || {})) {
    for (const method of classInfo.methods || []) {
      if (method.name === methodName) {
        bizImplClassName = className;
        bizImplFile = classInfo.filePath;
        bizMethodLineStart = method.lineNumber;
        bizMethodLineEnd = method.endLine || method.lineNumber + 20;
        break;
      }
    }
    if (bizImplFile) break;
  }

  // 计算相对路径并生成源码链接（自动检测 GitHub/GitLab）
  function getGitUrl(filePath, lineStart, lineEnd) {
    if (!projectInfo.gitRepo || !filePath) return '#';
    const isGitHub = projectInfo.gitRepo.includes('github.com');
    const baseUrl = isGitHub
      ? `https://github.com/${projectInfo.gitRepo}/blob/${projectInfo.baseBranch}`
      : `https://${projectInfo.gitlabHost || 'gitlab.example.com'}/${projectInfo.gitRepo}/-/blob/${projectInfo.baseBranch}`;
    const projectRoot = projectInfo.projectRoot || '';
    let relativePath = '';
    if (filePath.includes('/src/')) {
      relativePath = filePath.substring(filePath.indexOf('/src/') + 1);
    } else if (filePath.includes('/target/')) {
      relativePath = filePath.substring(filePath.indexOf('/target/') + 1);
    } else {
      relativePath = filePath.split('/').slice(-3).join('/');
    }
    if (lineStart && lineEnd) {
      return `${baseUrl}/${relativePath}#L${lineStart}-${lineEnd}`;
    } else if (lineStart) {
      return `${baseUrl}/${relativePath}#L${lineStart}`;
    }
    return `${baseUrl}/${relativePath}`;
  }

  // 获取文件名和带行号的显示文本
  const grpcFileName = grpcImplFile ? grpcImplFile.split('/').pop() : (grpcImplClassName || serviceName + 'GrpcImpl') + '.java';
  const bizFileName = bizImplFile ? bizImplFile.split('/').pop() : (bizImplClassName || 'Service') + '.java';

  // 构建带行号的显示文本
  const grpcFileNameWithLine = (grpcMethodLineStart && grpcMethodLineEnd)
    ? grpcFileName + ' (L' + grpcMethodLineStart + '-' + grpcMethodLineEnd + ')'
    : grpcFileName;
  const bizFileNameWithLine = (bizMethodLineStart && bizMethodLineEnd)
    ? bizFileName + ' (L' + bizMethodLineStart + '-' + bizMethodLineEnd + ')'
    : bizFileName;

  const grpcUrl = getGitUrl(grpcImplFile, grpcMethodLineStart, grpcMethodLineEnd);
  const bizUrl = getGitUrl(bizImplFile, bizMethodLineStart, bizMethodLineEnd);

  // Proto 文件链接 - 使用实际的 proto 文件路径
  let protoUrl = '#';
  if (projectInfo.gitRepo && protoFile) {
    const isGitHub = projectInfo.gitRepo.includes('github.com');
    const baseUrl = isGitHub
      ? 'https://github.com/' + projectInfo.gitRepo + '/blob/' + projectInfo.baseBranch
      : 'https://' + (projectInfo.gitlabHost || 'gitlab.example.com') + '/' + projectInfo.gitRepo + '/-/blob/' + projectInfo.baseBranch;
    // 提取相对路径，保留完整的模块路径
    let relativePath = '';
    // 通用匹配: 识别 *-proto 模块目录
    const protoModuleMatch = protoFile.match(/\/([^/]+-proto)\//);
    if (protoModuleMatch) {
      // 保留 proto 模块完整路径
      relativePath = protoFile.substring(protoFile.indexOf('/' + protoModuleMatch[1] + '/') + 1);
    } else if (protoFile.includes('/src/main/proto/')) {
      // 保留 src/main/proto 路径
      relativePath = protoFile.substring(protoFile.indexOf('/src/main/proto/') + 1);
    } else if (protoFile.includes('/proto/')) {
      // 从 proto 目录开始保留
      const protoIndex = protoFile.indexOf('/proto/');
      const beforeProto = protoFile.substring(0, protoIndex);
      const moduleName = beforeProto.split('/').pop();
      relativePath = moduleName + protoFile.substring(protoIndex);
    } else {
      relativePath = protoFile.split('/').slice(-3).join('/');
    }
    protoUrl = baseUrl + '/' + relativePath + '#L' + protoLineStart;
  }
  const protoFileName = protoFile ? protoFile.split('/').pop() : 'service.proto';
  const protoFileNameWithLine = protoLineStart ? protoFileName + ' (L' + protoLineStart + ')' : protoFileName;

  // 生成 gRPC 入口代码
  const grpcEntryCode = grpcImplFile
    ? `// gRPC 入口层 - ${grpcImplClassName}\npublic void ${methodName}(${inputType} request, StreamObserver<${outputType}> responseObserver) {\n    responseObserver.onNext(appService.${methodName}(request));\n    responseObserver.onCompleted();\n}`
    : `// TODO: 补充 gRPC 入口代码\npublic ${outputType} ${methodName}(${inputType} request) {\n    // 实现代码\n}`;

  // 生成业务逻辑代码
  const bizLogicCode = bizImplFile
    ? `// 业务逻辑实现 - ${bizImplClassName}\npublic ${outputType} ${methodName}(${inputType} request) {\n    // 具体实现见源码...\n    // 行号: ${bizMethodLineStart}-${bizMethodLineEnd}\n}`
    : `// TODO: 补充业务逻辑实现\npublic ${outputType} ${methodName}(${inputType} request) {\n    // 实现代码\n}`;

  // 生成输出类型的 message 定义
  let responseDef = '';
  if (protoInfo.messages[outputType]) {
    responseDef = `\n\nmessage ${outputType} {\n`;
    for (const field of protoInfo.messages[outputType].fields) {
      responseDef += `    ${field.repeated ? 'repeated ' : ''}${field.type} ${field.name} = ${field.number};\n`;
    }
    responseDef += '}';
  }


  // 生成 Java Client 调用示例
  const javaClientExample = generateJavaClientExample(methodName, inputType, outputType, protoInfo);

  // 生成使用场景
  const usageScenarios = generateUsageScenarios(methodName, bizMethodInfo, protoInfo.messages[inputType]);

  // 生成注意事项
  const warnings = generateWarnings(bizMethodInfo, protoInfo.messages[inputType]);

  // 生成相关接口
  const relatedApis = generateRelatedApis(methodName, serviceName, protoInfo.services);

  return `# ${methodName}

## 接口定义

${comments || generateDescriptionFromMethod(methodName, protoInfo.messages[inputType])}

### Proto 定义

\`\`\`protobuf
${protoDef}${requestDef}${responseDef}
\`\`\`

**Proto 源码**: [${protoFileNameWithLine}](${protoUrl})

---

## 调用流程

\`\`\`mermaid
flowchart TD
    A[gRPC Client] -->|1. ${methodName}| B[${serviceName}.${methodName}]
    B -->|2. 参数校验| C[校验逻辑]
    B -->|3. 调用业务层| D[${bizImplClassName || '业务逻辑层'}]
    D -->|4. 数据操作| E[(数据库)]
    D -->|5. 返回结果| F[${outputType}]
    F --> B
    B --> G[返回响应]
\`\`\`

### 流程说明

| 步骤 | 组件 | 说明 |
|------|------|------|
| 1 | gRPC Client | 调用 ${methodName} RPC 接口 |
| 2 | ${serviceName} | 接收 gRPC 请求，参数校验 |
| 3-4 | ${bizImplClassName || '业务逻辑层'} | 执行核心业务逻辑 |
| 5 | 返回 | 封装响应结果 |

---

## 核心逻辑实现

### 1. gRPC 入口层

\`\`\`java
${grpcEntryCode}
\`\`\`

**源码位置**: [${grpcFileNameWithLine}](${grpcUrl})

### 2. 业务逻辑层

\`\`\`java
${bizLogicCode}
\`\`\`

**源码位置**: [${bizFileNameWithLine}](${bizUrl})

---

## 数据模型

### ${inputType}

| 字段 | 类型 | 说明 | 必填 |
|------|------|------|------|
${protoInfo.messages[inputType] ? protoInfo.messages[inputType].fields.map(f => `| ${f.name} | ${f.repeated ? 'repeated ' : ''}${f.type} | ${f.comments || getFieldDescription(f.name)} | ${isRequiredField(f.name) ? '是' : ''} |`).join('\n') : '| TODO | | | |'}

### ${outputType}

| 字段 | 类型 | 说明 |
|------|------|------|
${protoInfo.messages[outputType] ? protoInfo.messages[outputType].fields.map(f => `| ${f.name} | ${f.repeated ? 'repeated ' : ''}${f.type} | ${f.comments || getFieldDescription(f.name)} |`).join('\n') : '| TODO | | |'}

---

## 调用示例

### Java Client

\`\`\`java
${javaClientExample}
\`\`\`

### curl（通过网关）

\`\`\`bash
# gRPC 接口需要通过 gRPC 客户端调用
# 如需 HTTP 访问，请通过网关转发的 REST 接口
\`\`\`

### 响应示例

\`\`\`json
${generateJsonExample(protoInfo.messages[outputType])}
\`\`\`

---

## 总结

### 使用场景

${usageScenarios}

### 关键注意点

<div class="info-box warning">
<strong>⚠️ 注意事项</strong>

${warnings}
</div>

### 相关接口

| 接口 | 说明 |
|------|------|
${relatedApis}
`;
}

// 辅助函数：生成字段描述
function getFieldDescription(fieldName) {
  const descriptions = {
    id: '唯一标识ID',
    name: '名称',
    namespace: '命名空间',
    appId: '应用ID',
    topic: 'Topic名称',
    description: '描述信息',
    loginUserId: '操作用户ID',
    loginUserName: '操作用户名',
    shardCount: '分区数量',
    publishRate: '发布速率限制(条/秒)',
    publishRateInByte: '发布速率限制(字节/秒)',
    consumerInMsg: '消费速率限制(条/秒)',
    consumerInByte: '消费速率限制(字节/秒)',
    pageNo: '页码，从1开始',
    pageSize: '每页大小',
    total: '总记录数',
    pages: '总页数',
    size: '当前页记录数',
    list: '数据列表',
    apps: '授权应用列表'
  };
  return descriptions[fieldName] || '';
}

// 辅助函数：判断是否必填字段
function isRequiredField(fieldName) {
  const requiredFields = ['name', 'namespace', 'appId', 'topic', 'pageNo', 'pageSize'];
  return requiredFields.includes(fieldName);
}

// 生成接口描述
function generateDescriptionFromMethod(methodName, inputMessage) {
  const descriptions = {
    addTopic: '创建新的 Topic，包括设置分区数、授权应用、速率限制等配置',
    editTopic: '修改已有 Topic 的配置信息',
    deleteTopic: '删除指定的 Topic',
    getTopic: '查询单个 Topic 的详细信息',
    PageListTopic: '分页查询 Topic 列表',
    listAppTopic: '查询指定应用下的所有 Topic',
    addSubscription: '为 Topic 创建新的订阅',
    editSubscription: '修改订阅配置',
    deleteSubscription: '删除指定的订阅',
    pageListSubscription: '分页查询 Topic 的订阅列表',
    checkTopicPermission: '检查对 Topic 的权限',
    checkSubPermission: '检查对订阅的权限',
    getMetric: '获取监控指标数据',
    getMessage: '获取消息详情',
    skipMessage: '跳过指定消息',
    skipAllMessage: '跳过所有消息',
    getDashboard: '获取监控大盘链接',
    resetOffset: '重置消费位点',
    queryTrace: '查询消息链路追踪',
    GetMessageById: '根据消息ID查询消息',
    GetSubscriptCursor: '查询订阅者游标信息',
    GetHoleMessageIdList: '查询消息空洞ID列表',
    SkipRangeMessage: '跳过指定范围的消息',
    previewUnloadBundle: '预览将被卸载的 Bundle',
    unloadBundle: '执行 Bundle 卸载',
    queryPrestoList: '通过 Presto 查询消息',
    querySubscription: '查询订阅信息'
  };
  return descriptions[methodName] || '执行指定的业务操作';
}

// 生成 Java Client 调用示例
function generateJavaClientExample(methodName, inputType, outputType, protoInfo) {
  const inputFields = protoInfo.messages[inputType]?.fields || [];
  const outputFields = protoInfo.messages[outputType]?.fields || [];

  // 构建请求参数示例
  const fieldExamples = inputFields.slice(0, 5).map(f => {
    const value = getExampleValue(f.type, f.name);
    return `        .set${capitalizeFirst(f.name)}(${value})`;
  }).join('\n');

  return `// 创建 gRPC Channel
ManagedChannel channel = ManagedChannelBuilder
    .forAddress("localhost", 9090)
    .usePlaintext()
    .build();

try {
    // 创建客户端 Stub
    MqManagerServiceGrpc.MqManagerServiceBlockingStub stub =
        MqManagerServiceGrpc.newBlockingStub(channel);

    // 构建请求
    ${inputType} request = ${inputType}.newBuilder()
${fieldExamples}
        .build();

    // 调用 RPC 方法
    ${outputType} response = stub.${methodName}(request);

    // 处理响应
    System.out.println("Response: " + response);
} finally {
    channel.shutdown();
}`;
}

// 生成示例值
function getExampleValue(type, fieldName) {
  if (fieldName === 'id') return '"123456"';
  if (fieldName === 'name') return '"my-topic"';
  if (fieldName === 'namespace') return '"dev"';
  if (fieldName === 'appId') return '"app-001"';
  if (fieldName === 'topic') return '"persistent://dev/my-topic"';
  if (fieldName === 'pageNo') return '1';
  if (fieldName === 'pageSize') return '20';
  if (fieldName.includes('Rate') || fieldName.includes('Count')) return '1000';
  if (type === 'string') return '"example"';
  if (type === 'int32' || type === 'int64') return '1';
  if (type === 'bool') return 'true';
  if (type === 'bytes') return 'ByteString.copyFromUtf8("data")';
  return '""';
}

// 生成 JSON 响应示例
function generateJsonExample(message) {
  if (!message || !message.fields) return '{\n  // 无返回值\n}';

  const fields = message.fields.slice(0, 5).map(f => {
    const value = getJsonExampleValue(f.type, f.name);
    return `  "${f.name}": ${value}`;
  });

  return `{\n${fields.join(',\n')}${message.fields.length > 5 ? ',\n  // ... more fields' : ''}\n}`;
}

function getJsonExampleValue(type, fieldName) {
  if (fieldName === 'id') return '"123456789"';
  if (fieldName === 'name') return '"example-topic"';
  if (type === 'string') return '"string_value"';
  if (type === 'int32' || type === 'int64') return '12345';
  if (type === 'double' || type === 'float') return '123.45';
  if (type === 'bool') return 'true';
  if (type.startsWith('repeated')) return '[]';
  return '""';
}

// 生成使用场景
function generateUsageScenarios(methodName, bizMethodInfo, inputMessage) {
  const scenarios = [];
  const analysis = bizMethodInfo?.analysis || {};

  // 基于方法名推断场景
  if (methodName.includes('add') || methodName.includes('create')) {
    scenarios.push('1. **创建资源**: 当需要新建 Topic 或订阅时使用此接口');
    scenarios.push('2. **初始化配置**: 设置资源的基本属性、权限和限制');
  } else if (methodName.includes('edit') || methodName.includes('update')) {
    scenarios.push('1. **修改配置**: 调整已有资源的配置参数');
    scenarios.push('2. **权限变更**: 更新授权应用列表或访问权限');
  } else if (methodName.includes('delete') || methodName.includes('remove')) {
    scenarios.push('1. **清理资源**: 删除不再使用的 Topic 或订阅');
    scenarios.push('2. **下线服务**: 配合应用下线流程清理相关资源');
  } else if (methodName.includes('get') || methodName.includes('query')) {
    scenarios.push('1. **查询详情**: 获取资源的详细配置和状态信息');
    scenarios.push('2. **监控排查**: 查看资源运行情况用于问题排查');
  } else if (methodName.includes('list') || methodName.includes('page')) {
    scenarios.push('1. **列表展示**: 管理后台展示资源列表');
    scenarios.push('2. **批量操作**: 对多个资源进行批量管理');
  } else if (methodName.includes('check') || methodName.includes('verify')) {
    scenarios.push('1. **权限校验**: 操作前验证用户是否有权限');
    scenarios.push('2. **前置检查**: 执行业务操作前的条件检查');
  } else {
    scenarios.push('1. **业务操作**: 执行特定的业务逻辑');
    scenarios.push('2. **数据管理**: 管理系统中的数据资源');
  }

  // 基于代码分析添加场景
  if (analysis.databaseOps?.length > 0) {
    scenarios.push(`3. **数据持久化**: 涉及数据库操作，确保数据一致性`);
  }
  if (analysis.externalCalls?.length > 0) {
    scenarios.push(`4. **外部依赖**: 调用外部服务完成业务逻辑`);
  }

  return scenarios.join('\n');
}

// 生成注意事项
function generateWarnings(bizMethodInfo, inputMessage) {
  const warnings = [];
  const analysis = bizMethodInfo?.analysis || {};
  const fields = inputMessage?.fields || [];

  // 基于代码分析
  if (analysis.validations?.length > 0) {
    warnings.push(`1. **参数校验**: 请确保传入参数符合要求，特别是必填字段`);
  }
  if (analysis.exceptionHandling?.length > 0) {
    warnings.push(`2. **异常处理**: 调用方需要处理可能的异常情况`);
  }
  if (analysis.databaseOps?.length > 0) {
    warnings.push(`3. **数据一致性**: 操作会影响数据库状态，请谨慎操作`);
  }
  if (analysis.externalCalls?.length > 0) {
    warnings.push(`4. **外部依赖**: 依赖外部服务，可能受网络因素影响`);
  }

  // 基于字段推断
  const hasRateLimit = fields.some(f => f.name.includes('Rate'));
  if (hasRateLimit) {
    warnings.push(`5. **速率限制**: 请合理设置速率限制，避免影响业务性能`);
  }

  if (warnings.length === 0) {
    warnings.push('1. 请确保传入参数正确');
    warnings.push('2. 调用前检查权限');
  }

  return warnings.join('\n');
}

// 生成相关接口
function generateRelatedApis(currentMethodName, currentService, services) {
  const apis = [];

  for (const service of services || []) {
    // 只显示同一服务的其他方法
    if (service.name !== currentService) continue;

    for (const method of service.methods || []) {
      // 跳过当前接口
      if (method.name === currentMethodName) continue;

      // 找到相关接口（同一服务的其他方法）
      const link = `[${method.name}](service/${method.name}.md)`;
      apis.push(`| ${link} | ${method.comments || '相关接口'} |`);
    }
  }

  return apis.slice(0, 5).join('\n') || '| - | - |';
}

// 工具函数
function capitalizeFirst(str) {
  return str.charAt(0).toUpperCase() + str.slice(1);
}

// 导航数据文件模板 - 用于动态渲染树形导航
function navDataJs(projectInfo, sections) {
  return `/**
 * ${projectInfo.name} - Navigation Data
 *
 * Hierarchical navigation tree. Paths are relative to the wiki root.
 * The renderer (nav.js) automatically prepends the correct number of
 * "../" segments based on the current page's depth.
 */
window.NAV_DATA = {
    title: "${projectInfo.name}",
    subtitle: "${projectInfo.description || '项目 Wiki'}",
    sections: ${JSON.stringify(sections, null, 4)}
};
`;
}

module.exports = {
  indexHtml,
  generateServiceNav,
  generateServiceCards,
  styleCss,
  navJs,
  navJsSpa,
  navDataJs,
  systemArchitectureMd,
  coreFeaturesMd,
  erDiagramMd,
  serviceMd
};
