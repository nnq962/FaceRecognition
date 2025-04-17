document.addEventListener('DOMContentLoaded', () => {
    // Cấu hình API
    // const API_BASE_URL = 'http://localhost:5543'; // Thay đổi URL này nếu API chạy ở port/host khác
    
    // Các biến cục bộ
    let currentProcessId = null;
    let processList = {};
    let statusCheckInterval;
    let selectedSources = new Set();
    
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
        setupTimeToSaveControls();
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
        
        // Xử lý sự kiện với toàn bộ option-item
        document.querySelectorAll('.option-item').forEach(optionItem => {
            optionItem.addEventListener('click', (e) => {
                // Bỏ qua nếu click vào nút tăng/giảm hoặc ô disabled
                if (e.target.closest('.param-btn') || optionItem.classList.contains('disabled')) {
                    return;
                }

                const checkbox = optionItem.querySelector('input[type="checkbox"]');
                checkbox.checked = !checkbox.checked;
                
                if (checkbox.checked) {
                    optionItem.classList.add('selected');
                } else {
                    optionItem.classList.remove('selected');
                }
                
                // Xử lý tùy chọn phụ thuộc
                handleDependentOptions();
            });
        });
        
        // Ngăn sự kiện click trên checkbox lan tỏa tới option-item
        document.querySelectorAll('.option-item input[type="checkbox"]').forEach(checkbox => {
            checkbox.addEventListener('click', (e) => {
                e.stopPropagation();
                
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
    }
    
    /**
     * Thiết lập điều khiển cho thời gian lưu
     */
    function setupTimeToSaveControls() {
        const exportDataOption = document.querySelector('.option-item[data-option="export_data"]');
        const timeValueElement = exportDataOption.querySelector('.param-text');
        
        // Lấy giá trị ban đầu
        let timeValue = parseInt(timeValueElement.textContent) || 3;
        
        // Thêm sự kiện wheel (lăn chuột) vào option-item
        exportDataOption.addEventListener('wheel', (e) => {
            e.preventDefault(); // Ngăn trang cuộn theo
            
            if (e.deltaY < 0) {
                // Cuộn lên (tăng giá trị)
                timeValue += 1;
                timeValueElement.textContent = timeValue;
            } else if (e.deltaY > 0 && timeValue > 1) {
                // Cuộn xuống (giảm giá trị)
                timeValue -= 1;
                timeValueElement.textContent = timeValue;
            }
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
     * Tải danh sách nguồn dữ liệu có sẵn từ API
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

                    // Xử lý sự kiện click
                    sourceItem.addEventListener('click', e => {
                        const cb = sourceItem.querySelector('input[type="checkbox"]');
                        cb.checked = !cb.checked;
                        sourceItem.classList.toggle('selected', cb.checked);
                    
                        if (cb.checked) selectedSources.add(source.id);
                        else selectedSources.delete(source.id);
                    });  
                    
                    sourcesContainer.appendChild(sourceItem);
                });
            })
            .catch(error => {
                console.error('Lỗi khi tải nguồn dữ liệu:', error);
                sourcesContainer.innerHTML = '<p style="white-space: nowrap;">Không thể tải nguồn dữ liệu. Vui lòng thử lại sau.</p>';
            });
    }
    
    /**
     * Bắt đầu tiến trình mới
     */
    function startProcess() {
        // 1. Kiểm tra xem đã chọn nguồn dữ liệu chưa
        if (selectedSources.size === 0) {
          showToast('Vui lòng chọn ít nhất một nguồn dữ liệu!', 'error');
          return;
        }
      
        // 2. Thu thập các tùy chọn
        const options = {};
        document.querySelectorAll('.option-item').forEach(item => {
        const cb = item.querySelector('input[type="checkbox"]');
        if (!cb || !cb.checked || item.classList.contains('disabled')) return;

        const opt = item.dataset.option;
        if (opt === 'export_data') {
            // ghi nhận bật export_data...
            options.export_data = true;
            // ...và thêm time_to_save với giá trị n
            const n = parseInt(
            item.querySelector('.param-text').textContent,
            10
            ) || 0;
            options.time_to_save = n;
        } else {
            // các option bình thường
            options[opt] = true;
        }
        });
      
        // 3. Xây payload
        const processData = {
          process_name: processNameInput.value || 'Tiến trình mới',
          sources: Array.from(selectedSources),
          options: options
        };
      
        // 4. Thông báo đang gửi
        showToast('Đang bắt đầu tiến trình...', 'info');
      
        // 5. Gửi request lên server
        fetch('/run_process', {
          method: 'POST',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify(processData)
        })
          .then(response => response.json())
          .then(data => {
            if (data.status === 'success') {
              showToast(data.message, 'success');
              // Làm mới danh sách và chọn tiến trình mới
              refreshProcessList(data.process_id);
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
        
        // Hiển thị đang xử lý
        showToast('Đang dừng tiến trình...', 'info');
        
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
                refreshProcessList(currentProcessId);
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
                showToast('Không thể tải danh sách tiến trình', 'error');
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
                
                // Cập nhật trạng thái trong processList
                if (processList[currentProcessId]) {
                    processList[currentProcessId].running = data.running;
                    
                    // Cập nhật UI của tiến trình trong danh sách
                    const item = document.querySelector(`.process-item[data-process-id="${currentProcessId}"]`);
                    if (item) {
                        // Cập nhật class
                        item.classList.remove('running', 'stopped');
                        item.classList.add(data.running ? 'running' : 'stopped');
                        
                        // Cập nhật status
                        const statusElement = item.querySelector('.process-status');
                        if (statusElement) {
                            statusElement.className = `process-status ${data.running ? 'status-running' : 'status-stopped'}`;
                            statusElement.textContent = data.running ? 'Đang chạy' : 'Đã dừng';
                        }
                    }
                }
                
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
                
                // Nếu tiến trình đã dừng, dừng kiểm tra trạng thái
                if (!data.running) {
                    clearInterval(statusCheckInterval);
                }
            })
            .catch(error => {
                console.error('Lỗi khi cập nhật output:', error);
                terminal.innerHTML = '<p class="terminal-line">Không thể kết nối đến server để lấy log.</p>';
            });
    }
    
    /**
     * Xóa tất cả các tùy chọn đã chọn
     */
    function clearOptions() {
        // Xóa chọn tất cả các nguồn (checkbox)
        selectedSources.clear();
        document.querySelectorAll('.source-item').forEach(item => {
            const cb = item.querySelector('input[type="checkbox"]');
            if (cb) {
                cb.checked = false;
                item.classList.remove('selected');
            }
        });
    
        // Xóa chọn tất cả các tùy chọn
        document.querySelectorAll('.option-item').forEach(item => {
            const cb = item.querySelector('input[type="checkbox"]');
            if (cb) {
                cb.checked = false;
                item.classList.remove('selected');
            }
        });
    
        // Reset giá trị "Lưu dữ liệu mỗi n giây" về default = 3
        const exportParam = document.querySelector('.option-item[data-option="export_data"] .param-text');
        if (exportParam) {
            exportParam.textContent = '3';
        }
    
        // Reset tên tiến trình
        processNameInput.value = '';
    
        // Chạy lại logic phụ thuộc (face_emotion, raise_hand, ...)
        handleDependentOptions();
    
        // Thông báo
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