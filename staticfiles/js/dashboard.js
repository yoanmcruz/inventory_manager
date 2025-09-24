class DynamicDashboard {
    constructor() {
        console.log('DynamicDashboard: Inicializando...');
        
        this.statsCards = document.getElementById('statsCards');
        this.alertsContainer = document.getElementById('alertsContainer');
        this.recentMaintenance = document.getElementById('recentMaintenance');
        this.recentTickets = document.getElementById('recentTickets');
        this.loadingIndicator = document.getElementById('loadingIndicator');
        this.refreshBtn = document.getElementById('refreshBtn');
        
        this.charts = {};
        this.autoRefreshInterval = null;
        this.currentAutoRefresh = 0;
        
        this.init();
    }
    
    init() {
        console.log('DynamicDashboard: Configurando event listeners...');
        this.setupEventListeners();
        this.loadData(); // Cargar datos inmediatamente
    }
    
    setupEventListeners() {
        // Botón de actualización manual
        if (this.refreshBtn) {
            this.refreshBtn.addEventListener('click', () => {
                console.log('DynamicDashboard: Actualización manual solicitada');
                this.loadData();
            });
        }
        
        // Auto-actualización
        document.querySelectorAll('.auto-refresh').forEach(item => {
            item.addEventListener('click', (e) => {
                e.preventDefault();
                const interval = parseInt(item.dataset.interval);
                console.log(`DynamicDashboard: Auto-actualización configurada a ${interval}ms`);
                this.setAutoRefresh(interval);
            });
        });
        
        // Toggle entre gráfico de torta y barras
        const chartToggle = document.getElementById('chartTypeToggle');
        if (chartToggle) {
            chartToggle.addEventListener('change', (e) => {
                this.toggleChartType(e.target.checked);
            });
        }
    }
    
    setAutoRefresh(interval) {
        this.currentAutoRefresh = interval;
        
        if (this.autoRefreshInterval) {
            clearInterval(this.autoRefreshInterval);
        }
        
        if (interval > 0) {
            this.autoRefreshInterval = setInterval(() => {
                console.log('DynamicDashboard: Auto-actualización ejecutándose...');
                this.loadData();
            }, interval);
            
            this.showNotification(`Auto-actualización activada cada ${interval/1000} segundos`, 'info');
        } else {
            this.showNotification('Auto-actualización desactivada', 'warning');
        }
    }
    
    async loadData() {
        console.log('DynamicDashboard: Cargando datos...');
        this.showLoading(true);
        
        try {
            const baseUrl = window.location.origin;
            const urls = [
                `${baseUrl}/inventory/api/dashboard/stats/`,
                `${baseUrl}/inventory/api/dashboard/equipment-chart/`,
                `${baseUrl}/inventory/api/dashboard/recent-activity/`
            ];
            
            console.log('DynamicDashboard: URLs a cargar:', urls);
            
            const [statsResponse, chartResponse, activityResponse] = await Promise.all([
                fetch(urls[0], { credentials: 'same-origin' }),
                fetch(urls[1], { credentials: 'same-origin' }),
                fetch(urls[2], { credentials: 'same-origin' })
            ]);
            
            if (!statsResponse.ok) throw new Error(`Stats API: ${statsResponse.status}`);
            if (!chartResponse.ok) throw new Error(`Chart API: ${chartResponse.status}`);
            if (!activityResponse.ok) throw new Error(`Activity API: ${activityResponse.status}`);
            
            const stats = await statsResponse.json();
            const chartData = await chartResponse.json();
            const activity = await activityResponse.json();
            
            console.log('DynamicDashboard: Datos recibidos:', { stats, chartData, activity });
            
            this.updateStatsCards(stats);
            this.updateAlerts(stats.alerts);
            this.updateRecentActivity(activity);
            
            // Inicializar gráficos si no existen
            if (!this.charts.typeChart) {
                this.initializeCharts();
            }
            this.updateCharts(chartData);
            
            this.showNotification('Datos actualizados correctamente', 'success');
            
        } catch (error) {
            console.error('DynamicDashboard: Error loading data:', error);
            this.showNotification(`Error al cargar los datos: ${error.message}`, 'danger');
            
            // Mostrar datos de fallback
            this.showFallbackData();
        }
        
        this.showLoading(false);
    }
    
    updateStatsCards(stats) {
        const cards = [
            {
                title: 'Total Equipos',
                value: stats.equipment.total,
                icon: 'bi-pc-display',
                color: 'primary',
                link: '/inventory/equipment/'
            },
            {
                title: 'Disponibles',
                value: stats.equipment.available,
                icon: 'bi-check-circle',
                color: 'success',
                filter: 'status=AVA'
            },
            {
                title: 'En Uso',
                value: stats.equipment.in_use,
                icon: 'bi-person-check',
                color: 'info',
                filter: 'status=INU'
            },
            {
                title: 'En Reparación',
                value: stats.equipment.in_repair,
                icon: 'bi-tools',
                color: 'warning',
                filter: 'status=REP'
            },
            {
                title: 'Tickets Abiertos',
                value: stats.tickets.open,
                icon: 'bi-ticket-perforated',
                color: 'secondary',
                link: '/inventory/support/tickets/?status=OPEN'
            },
            {
                title: 'Tickets Críticos',
                value: stats.tickets.critical,
                icon: 'bi-exclamation-triangle',
                color: 'danger',
                link: '/inventory/support/tickets/?priority=CRITICAL'
            }
        ];
        
        this.statsCards.innerHTML = cards.map(card => `
            <div class="col-xl-2 col-md-4 col-sm-6 mb-3">
                <div class="card text-white bg-${card.color} h-100 card-hover">
                    <div class="card-body">
                        <div class="d-flex justify-content-between align-items-center">
                            <div>
                                <h6 class="card-title">${card.title}</h6>
                                <h2 class="card-text">${card.value}</h2>
                            </div>
                            <i class="bi ${card.icon} display-4 opacity-50"></i>
                        </div>
                    </div>
                    ${card.link ? `<a href="${card.link}${card.filter ? '?' + card.filter : ''}" class="stretched-link"></a>` : ''}
                </div>
            </div>
        `).join('');
    }
    
    updateAlerts(alerts) {
        const alertItems = [];
        
        if (alerts.warranty_expiring > 0) {
            alertItems.push({
                title: 'Garantías por Vencer',
                count: alerts.warranty_expiring,
                icon: 'bi-clock',
                color: 'warning',
                description: 'Equipos con garantía que expira en los próximos 30 días'
            });
        }
        
        if (alerts.maintenance_pending > 0) {
            alertItems.push({
                title: 'Mantenimientos Pendientes',
                count: alerts.maintenance_pending,
                icon: 'bi-tools',
                color: 'info',
                description: 'Mantenimientos en progreso sin finalizar'
            });
        }
        
        if (alertItems.length === 0) {
            alertItems.push({
                title: 'Sin Alertas',
                count: 0,
                icon: 'bi-check-circle',
                color: 'success',
                description: 'No hay alertas críticas en este momento'
            });
        }
        
        this.alertsContainer.innerHTML = alertItems.map(alert => `
            <div class="col-md-6 mb-3">
                <div class="card border-${alert.color}">
                    <div class="card-body">
                        <div class="d-flex align-items-center">
                            <i class="bi ${alert.icon} text-${alert.color} fs-1 me-3"></i>
                            <div>
                                <h5 class="card-title">${alert.title}</h5>
                                <h2 class="text-${alert.color}">${alert.count}</h2>
                                <p class="card-text text-muted small">${alert.description}</p>
                            </div>
                        </div>
                    </div>
                </div>
            </div>
        `).join('');
    }
    
    initializeCharts() {
        console.log('DynamicDashboard: Inicializando gráficos...');
        
        // Gráfico de equipos por tipo
        const typeCtx = document.getElementById('equipmentTypeChart');
        if (typeCtx) {
            this.charts.typeChart = new Chart(typeCtx, {
                type: 'doughnut',
                data: { datasets: [{}] },
                options: {
                    responsive: true,
                    plugins: {
                        legend: { position: 'bottom' }
                    }
                }
            });
        }
        
        // Gráfico de equipos por estado
        const statusCtx = document.getElementById('equipmentStatusChart');
        if (statusCtx) {
            this.charts.statusChart = new Chart(statusCtx, {
                type: 'bar',
                data: { datasets: [{}] },
                options: {
                    responsive: true,
                    scales: { y: { beginAtZero: true } },
                    plugins: { legend: { display: false } }
                }
            });
        }
    }
    
    updateCharts(chartData) {
        if (this.charts.typeChart && chartData.by_type) {
            this.charts.typeChart.data = {
                labels: chartData.by_type.map(item => item.label),
                datasets: [{
                    data: chartData.by_type.map(item => item.count),
                    backgroundColor: this.generateColors(chartData.by_type.length, 0.8)
                }]
            };
            this.charts.typeChart.update();
        }
        
        if (this.charts.statusChart && chartData.by_status) {
            this.charts.statusChart.data = {
                labels: chartData.by_status.map(item => item.label),
                datasets: [{
                    data: chartData.by_status.map(item => item.count),
                    backgroundColor: this.generateColors(chartData.by_status.length, 0.8)
                }]
            };
            this.charts.statusChart.update();
        }
    }
    
    toggleChartType(showBars) {
        if (this.charts.typeChart) {
            this.charts.typeChart.config.type = showBars ? 'bar' : 'doughnut';
            this.charts.typeChart.update();
        }
    }
    
    updateRecentActivity(activity) {
        if (this.recentMaintenance && activity.maintenance) {
            this.recentMaintenance.innerHTML = activity.maintenance.map(item => `
                <div class="list-group-item">
                    <div class="d-flex w-100 justify-content-between">
                        <h6 class="mb-1">${item.title}</h6>
                        <small>${this.formatDate(item.start_date)}</small>
                    </div>
                    <p class="mb-1 small">${item.equipment_brand} ${item.equipment_model}</p>
                    <small class="text-muted">Por: ${item.technician_name}</small>
                </div>
            `).join('');
        }
        
        if (this.recentTickets && activity.tickets) {
            this.recentTickets.innerHTML = activity.tickets.map(item => `
                <div class="list-group-item">
                    <div class="d-flex w-100 justify-content-between">
                        <h6 class="mb-1">${item.title}</h6>
                        <span class="badge bg-${this.getPriorityColor(item.priority)}">${item.priority}</span>
                    </div>
                    <p class="mb-1 small">Estado: ${item.status}</p>
                    <small class="text-muted">Creado por: ${item.created_by_name}</small>
                </div>
            `).join('');
        }
    }
    
    showFallbackData() {
        this.statsCards.innerHTML = `
            <div class="col-12">
                <div class="alert alert-warning">
                    <h4>Datos no disponibles</h4>
                    <p>No se pudieron cargar los datos del dashboard. Verifica la conexión e intenta nuevamente.</p>
                </div>
            </div>
        `;
    }
    
    // Helper functions
    generateColors(count, opacity = 0.8) {
        const colors = [
            `rgba(54, 162, 235, ${opacity})`, `rgba(255, 99, 132, ${opacity})`,
            `rgba(255, 159, 64, ${opacity})`, `rgba(75, 192, 192, ${opacity})`,
            `rgba(153, 102, 255, ${opacity})`, `rgba(255, 205, 86, ${opacity})`
        ];
        return colors.slice(0, count);
    }
    
    getPriorityColor(priority) {
        const colorMap = { 'LOW': 'info', 'MED': 'warning', 'HIGH': 'danger', 'CRITICAL': 'dark' };
        return colorMap[priority] || 'secondary';
    }
    
    formatDate(dateString) {
        try {
            return new Date(dateString).toLocaleDateString('es-ES');
        } catch {
            return dateString;
        }
    }
    
    showLoading(show) {
        if (this.loadingIndicator) {
            this.loadingIndicator.classList.toggle('d-none', !show);
        }
        if (this.refreshBtn) {
            this.refreshBtn.disabled = show;
            this.refreshBtn.innerHTML = show ? 
                '<i class="bi bi-arrow-clockwise spinner"></i> Actualizando...' : 
                '<i class="bi bi-arrow-clockwise"></i> Actualizar';
        }
    }
    
    showNotification(message, type) {
        const toast = document.createElement('div');
        toast.className = `toast align-items-center text-white bg-${type} border-0`;
        toast.innerHTML = `
            <div class="d-flex">
                <div class="toast-body">${message}</div>
                <button type="button" class="btn-close btn-close-white me-2 m-auto" data-bs-dismiss="toast"></button>
            </div>
        `;
        
        document.body.appendChild(toast);
        const bsToast = new bootstrap.Toast(toast, { delay: 3000 });
        bsToast.show();
        
        toast.addEventListener('hidden.bs.toast', () => {
            document.body.removeChild(toast);
        });
    }
}