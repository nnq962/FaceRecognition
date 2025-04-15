document.addEventListener('DOMContentLoaded', () => {
    // Các biến cục bộ
    let selectedSources = new Set();
    let currentProcessId = null;
    let processList = {};
    let statusCheckInterval;
    
    // Các phần tử DOM
    const sourcesContainer = document.getElementById('sources-container');
    const runBtn = document.getElementById('run-btn');
    const stopBtn = document.getElementById('stop-btn');
    const clearBtn = document.getElementById('clear-btn');
    const refreshBtn = document.getElementById('refresh-btn');
    const processListContainer = document.getElementById('process-list-container');
    const noProcessMessage = document.getElementById('no-process-message');
    const terminal = document.getElementById('terminal');
    const processNameInput = document.getElementById('process-name');
    const currentProcessName = document.getElementById('current-process-name');
    const processStatusIndicator = document.getElementById('process-status-indicator');
    
    // Khởi tạo
    initializeApp();
    
    /**
     * Khởi tạo ứng dụng
     */
    function initializeApp() {
        loadAvailableSources();
        setupEventListeners();
        refreshProcessList();
        handleDependentOptions();
    }
    
    /**
     * Thiết lập các event listener
     */
    function setupEventListeners() {
        // Nút chạy tiến trình
        runBtn.addEventListener('click', startProcess);
        
        // Nút dừng tiến trình
        stopBtn.addEventListener('click', stopProcess);
        
        // Nút làm mới danh sách tiến trình
        refreshBtn.addEventListener('click', refreshProcessList);
        
        // Nút xóa tùy chọn
        clearBtn.addEventListener('click', clearOptions);
        
        // Xử lý sự kiện với tùy chọn phụ thuộc
        document.querySelectorAll('.option-item input[type="checkbox"]').forEach(checkbox => {
            checkbox.addEventListener('change', (e) => {
                const optionItem = e.target.closest('.option-item');
                
                if (e.target.checked) {
                    optionItem.classList.add('selected');
                } else {
                    optionItem.classList.remove('selected');
                }
                
                // Xử lý tùy chọn phụ thuộc
                handleDependentOptions();
            });
        });
        
        // Xử lý sự kiện giá trị tùy chọn
        document.querySelectorAll('.option-param input').forEach(input => {
            input.addEventListener('click', (e) => {
                e.stopPropagation(); // Ngăn không cho checkbox thay đổi khi click vào input
            });
        });
    }
    
    /**
     * Xử lý các tùy chọn phụ thuộc
     */
    function handleDependentOptions() {
        // Xử lý cho face_emotion và raise_hand phụ thuộc vào face_recognition
        const faceRecognition = document.getElementById('face_recognition');
        const dependentOnFaceRecognition = document.querySelectorAll('[data-depends="face_recognition"]');
        
        dependentOnFaceRecognition.forEach(option => {
            if (!faceRecognition.checked) {
                option.classList.add('disabled');
                option.querySelector('input[type="checkbox"]').checked = false;
                option.classList.remove('selected');
            } else {
                option.classList.remove('disabled');
            }
        });
        
        // Xử lý cho time_to_save phụ thuộc vào export_data
        const exportData = document.getElementById('export_data');
        const dependentOnExportData = document.querySelectorAll('[data-depends="export_data"]');
        
        dependentOnExportData.forEach(option => {
            if (!exportData.checked) {
                option.classList.add('disabled');
                option.querySelector('input[type="checkbox"]').checked = false;
                option.classList.remove('selected');
            } else {
                option.classList.remove('disabled');
            }
        });
    }
    
    /**
     * Tải danh sách nguồn dữ liệu có sẵn
     */
    function loadAvailableSources() {
        fetch('/get_available_sources')
            .then(response => response.json())
            .then(sources => {
                sourcesContainer.innerHTML = '';
                
                sources.forEach(source => {
                    const sourceItem = document.createElement('div');
                    sourceItem.className = 'source-item';
                    sourceItem.dataset.sourceId = source.id;
                    
                    sourceItem.innerHTML = `
                        <input type="checkbox" id="source-${source.id}" value="${source.id}">
                        <label for="source-${source.id}">${source.name}</label>
                    `;
                    
                    sourceItem.addEventListener('click', (e) => {
                        const checkbox = sourceItem.querySelector('input[type="checkbox"]');
                        // Nếu click trực tiếp vào checkbox thì không toggle
                        if (e.target !== checkbox) {
                            checkbox.checked = !checkbox.checked;
                        }
                        
                        if (checkbox.checked) {
                            sourceItem.classList.add('selected');
                            selectedSources.add(source.id);
                        } else {
                            sourceItem.classList.remove('selected');
                            selectedSources.delete(source.id);
                        }
                    });
                    
                    sourcesContainer.appendChild(sourceItem);
                });
            })
            .catch(error => {
                console.error('Lỗi khi tải nguồn dữ liệu:', error);
                sourcesContainer.innerHTML = '<p>Không thể tải nguồn dữ liệu. Vui lòng thử lại sau.</p>';
            });
    }
    
    /**
     * Bắt đầu tiến trình mới
     */
    function startProcess() {
        // Kiểm tra xem đã chọn nguồn dữ liệu chưa
        if (selectedSources.size === 0) {
            alert('Vui lòng chọn ít nhất một nguồn dữ liệu!');
            return;
        }
        
        // Thu thập các tùy chọn
        const options = {};
        document.querySelectorAll('.option-item').forEach(item => {
            const checkbox = item.querySelector('input[type="checkbox"]');
            if (checkbox.checked && !item.classList.contains('disabled')) {
                const optionName = item.dataset.option;
                
                // Kiểm tra xem có tham số bổ sung không
                const paramInput = item.querySelector('.option-param input');
                if (paramInput && optionName === 'time_to_save') {
                    options[optionName] = paramInput.value;
                } else {
                    options[optionName] = true;
                }
            }
        });
        
        // Dữ liệu gửi tới server
        const processData = {
            process_name: processNameInput.value || 'Tiến trình mới',
            sources: Array.from(selectedSources),
            options: options
        };
        
        // Gửi yêu cầu
        fetch('/run_process', {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json'
            },
            body: JSON.stringify(processData)
        })
        .then(response => response.json())
        .then(data => {
            if (data.status === 'success') {
                // Thêm tiến trình mới vào danh sách và chọn nó
                const processId = data.process_id;
                refreshProcessList(processId);
                
                // Hiển thị thông báo
                showToast(data.message, 'success');
            } else {
                showToast(data.message, 'error');
            }
        })
        .catch(error => {
            console.error('Lỗi khi gửi yêu cầu:', error);
            showToast('Đã xảy ra lỗi khi kết nối với server!', 'error');
        });
    }
    
    /**
     * Dừng tiến trình hiện tại
     */
    function stopProcess() {
        if (!currentProcessId) return;
        
        fetch('/stop_process', {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json'
            },
            body: JSON.stringify({ process_id: currentProcessId })
        })
        .then(response => response.json())
        .then(data => {
            if (data.status === 'success') {
                showToast(data.message, 'success');
                // Cập nhật lại UI và danh sách
                refreshProcessList();
            } else {
                showToast(data.message, 'error');
            }
        })
        .catch(error => {
            console.error('Lỗi khi dừng tiến trình:', error);
            showToast('Đã xảy ra lỗi khi kết nối với server!', 'error');
        });
    }
    
    /**
     * Làm mới danh sách tiến trình
     */
    function refreshProcessList(selectProcessId = null) {
        fetch('/get_all_processes')
            .then(response => response.json())
            .then(data => {
                processList = data;
                updateProcessListUI(selectProcessId);
            })
            .catch(error => {
                console.error('Lỗi khi tải danh sách tiến trình:', error);
            });
    }
    
    /**
     * Cập nhật giao diện danh sách tiến trình
     */
    function updateProcessListUI(selectProcessId = null) {
        // Kiểm tra xem có tiến trình nào không
        const processIds = Object.keys(processList);
        
        if (processIds.length === 0) {
            processListContainer.innerHTML = '';
            noProcessMessage.style.display = 'block';
            terminal.innerHTML = '<p class="terminal-line">Chưa có tiến trình nào được chạy.</p>';
            currentProcessId = null;
            currentProcessName.textContent = 'Đầu ra tiến trình';
            stopBtn.disabled = true;
            processStatusIndicator.style.display = 'none';
            clearInterval(statusCheckInterval);
            return;
        }
        
        // Có tiến trình, ẩn thông báo
        noProcessMessage.style.display = 'none';
        processListContainer.innerHTML = '';
        
        // Thêm tiến trình vào danh sách
        for (const [id, process] of Object.entries(processList)) {
            const processItem = document.createElement('div');
            processItem.className = `process-item ${process.running ? 'running' : 'stopped'}`;
            processItem.dataset.processId = id;
            
            processItem.innerHTML = `
                <div class="process-item-header">
                    <div class="process-name">${process.name}</div>
                    <div class="process-status ${process.running ? 'status-running' : 'status-stopped'}">
                        ${process.running ? 'Đang chạy' : 'Đã dừng'}
                    </div>
                </div>
                <div class="process-details">
                    Bắt đầu: ${process.start_time}
                </div>
                <div class="process-command">${process.command}</div>
            `;
            
            processItem.addEventListener('click', () => {
                // Bỏ chọn tất cả các tiến trình khác
                document.querySelectorAll('.process-item').forEach(item => {
                    item.classList.remove('active');
                });
                
                // Chọn tiến trình hiện tại
                processItem.classList.add('active');
                selectProcess(id);
            });
            
            processListContainer.appendChild(processItem);
        }
        
        // Nếu có ID tiến trình được chỉ định để chọn
        if (selectProcessId && processList[selectProcessId]) {
            selectProcess(selectProcessId);
            // Đánh dấu tiến trình đó là active
            const item = document.querySelector(`.process-item[data-process-id="${selectProcessId}"]`);
            if (item) {
                item.classList.add('active');
            }
        } 
        // Nếu không có ID tiến trình được chỉ định, hoặc ID không tồn tại
        else if (!currentProcessId || !processList[currentProcessId]) {
            // Chọn tiến trình đầu tiên
            const firstProcessId = processIds[0];
            selectProcess(firstProcessId);
            // Đánh dấu tiến trình đầu tiên là active
            const item = document.querySelector(`.process-item[data-process-id="${firstProcessId}"]`);
            if (item) {
                item.classList.add('active');
            }
        } else {
            // Giữ nguyên tiến trình hiện tại và đánh dấu là active
            const item = document.querySelector(`.process-item[data-process-id="${currentProcessId}"]`);
            if (item) {
                item.classList.add('active');
            }
        }
    }
    
    /**
     * Chọn một tiến trình để xem
     */
    function selectProcess(processId) {
        // Đặt tiến trình hiện tại
        currentProcessId = processId;
        
        // Cập nhật UI
        const process = processList[processId];
        if (process) {
            currentProcessName.textContent = process.name;
            stopBtn.disabled = !process.running;
            processStatusIndicator.style.display = process.running ? 'inline-block' : 'none';
            
            // Cập nhật terminal và bắt đầu kiểm tra trạng thái
            updateTerminalOutput();
            
            // Hủy interval cũ nếu có
            if (statusCheckInterval) {
                clearInterval(statusCheckInterval);
            }
            
            // Bắt đầu kiểm tra trạng thái
            statusCheckInterval = setInterval(updateTerminalOutput, 1000);
        }
    }
    
    /**
     * Cập nhật output trong terminal
     */
    function updateTerminalOutput() {
        if (!currentProcessId) return;
        
        fetch(`/get_process_status?process_id=${currentProcessId}`)
            .then(response => response.json())
            .then(data => {
                if (data.status === 'error') {
                    terminal.innerHTML = `<p class="terminal-line">${data.message}</p>`;
                    clearInterval(statusCheckInterval);
                    return;
                }
                
                // Cập nhật UI
                stopBtn.disabled = !data.running;
                processStatusIndicator.style.display = data.running ? 'inline-block' : 'none';
                
                // Cập nhật output
                if (data.output && data.output.length > 0) {
                    terminal.innerHTML = '';
                    data.output.forEach(line => {
                        const lineElement = document.createElement('p');
                        lineElement.className = 'terminal-line';
                        lineElement.textContent = line;
                        terminal.appendChild(lineElement);
                    });
                    
                    // Cuộn xuống dưới cùng
                    terminal.scrollTop = terminal.scrollHeight;
                } else {
                    terminal.innerHTML = '<p class="terminal-line">Chưa có dữ liệu đầu ra.</p>';
                }
                
                // Nếu tiến trình đã dừng, cập nhật danh sách tiến trình
                if (!data.running) {
                    refreshProcessList();
                }
            })
            .catch(error => {
                console.error('Lỗi khi cập nhật output:', error);
            });
    }
    
    /**
     * Xóa tất cả các tùy chọn đã chọn
     */
    function clearOptions() {
        // Bỏ chọn tất cả các nguồn
        document.querySelectorAll('.source-item').forEach(item => {
            const checkbox = item.querySelector('input[type="checkbox"]');
            checkbox.checked = false;
            item.classList.remove('selected');
        });
        selectedSources.clear();
        
        // Bỏ chọn tất cả các tùy chọn
        document.querySelectorAll('.option-item').forEach(item => {
            const checkbox = item.querySelector('input[type="checkbox"]');
            checkbox.checked = false;
            item.classList.remove('selected');
        });
        
        // Đặt lại giá trị cho các tham số
        document.getElementById('time_to_save_value').value = '3';
        
        // Đặt lại tên tiến trình
        processNameInput.value = 'Tiến trình mới';
        
        // Xử lý lại tùy chọn phụ thuộc
        handleDependentOptions();
        
        showToast('Đã xóa tất cả tùy chọn!', 'success');
    }
    
    /**
     * Hiển thị thông báo
     */
    function showToast(message, type = 'info') {
        // Kiểm tra xem đã có toast container chưa
        let toastContainer = document.querySelector('.toast-container');
        
        if (!toastContainer) {
            toastContainer = document.createElement('div');
            toastContainer.className = 'toast-container';
            document.body.appendChild(toastContainer);
        }
        
        // Tạo toast
        const toast = document.createElement('div');
        toast.className = `toast toast-${type}`;
        
        // Icon
        const icon = document.createElement('i');
        icon.className = `fas ${type === 'success' ? 'fa-check-circle' : type === 'error' ? 'fa-exclamation-circle' : 'fa-info-circle'}`;
        icon.style.marginRight = '8px';
        
        // Text
        const text = document.createElement('span');
        text.textContent = message;
        
        toast.appendChild(icon);
        toast.appendChild(text);
        toastContainer.appendChild(toast);
        
        // Tự động ẩn sau 3 giây
        setTimeout(() => {
            toast.style.animation = 'fadeOut 0.3s';
            toast.addEventListener('animationend', () => {
                toast.remove();
                // Xóa container nếu không còn toast
                if (toastContainer.children.length === 0) {
                    toastContainer.remove();
                }
            });
        }, 3000);
    }
});