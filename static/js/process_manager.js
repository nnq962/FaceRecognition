document.addEventListener('DOMContentLoaded', () => {
    // Cấu hình API
    // const API_BASE_URL = 'http://localhost:5543'; // Thay đổi URL này nếu API chạy ở port/host khác

    // Các biến cục bộ
    let currentProcessId = null;
    let processList = {};
    let statusCheckInterval;
    let selectedSources = new Set();
    let userScrolled = false;

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

    const elementControl = document.getElementById("control");
    const elementTerminal = document.getElementById("terminal");
    const elementHeaderTerminal = document.getElementById("header-terminal");
    const elementProcess = document.getElementById("process-output");


    function updateTerminalHeight() {
        const browserHeight = window.innerHeight;
        const controlHeight = elementControl.offsetHeight;
        const headerTerminalHeight = elementHeaderTerminal.offsetHeight
        // Lấy chiều cao nhỏ hơn giữa control và browser
        const newHeight = controlHeight
        let height = (newHeight - 16)
        // Gán chiều cao cho terminal
        elementTerminal.style.height = `${height - 55 - headerTerminalHeight}px`;
        elementProcess.style.height = `${height}px`;

    }

    // Gọi lần đầu khi trang tải
    updateTerminalHeight();

    // Gọi lại khi control thay đổi kích thước
    const observer = new ResizeObserver(updateTerminalHeight);
    observer.observe(elementControl);

    // Gọi lại khi cửa sổ trình duyệt thay đổi kích thước
    window.addEventListener('resize', updateTerminalHeight);

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
        setupTerminalScrollTracking();
    }

    /**
     * Thiết lập các event listener
     */
    function setupEventListeners() {
        // Nút chạy tiến trình
        runBtn.addEventListener('click', () => {
            // Chế độ tạo tiến trình mới bình thường
            startProcess();
        });

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

    function setupTerminalScrollTracking() {
        terminal.addEventListener('scroll', function () {
            // Nếu user cuộn lên (không ở cuối cùng), đánh dấu là đã cuộn
            const isAtBottom = terminal.scrollHeight - terminal.scrollTop <= terminal.clientHeight + 50;
            userScrolled = !isAtBottom;
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
        // Kiểm tra xem đang trong chế độ chỉnh sửa hay không
        const isEditMode = runBtn.dataset.editMode === 'edit';
        const editId = runBtn.dataset.editId;

        // 1. Kiểm tra xem đã nhập tên tiến trình chưa
        if (!processNameInput.value.trim()) {
            showToast('Vui lòng nhập tên cho tiến trình!', 'error');
            return;
        }

        // 2. Kiểm tra xem đã chọn nguồn dữ liệu chưa
        if (selectedSources.size === 0) {
            showToast('Vui lòng chọn ít nhất một nguồn dữ liệu!', 'error');
            return;
        }

        // 3. Thu thập các tùy chọn
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

        // 4. Xây payload
        const processData = {
            process_name: processNameInput.value.trim(),
            sources: Array.from(selectedSources),
            options: options
        };

        // Nếu là chế độ edit, thêm process_id vào payload
        if (isEditMode && editId) {
            processData.process_id = editId;
        }

        // 5. Thông báo đang gửi
        showToast(`Đang ${isEditMode ? 'cập nhật' : 'bắt đầu'} tiến trình...`, 'info');

        // 6. Gửi request lên server
        const endpoint = isEditMode ? '/update_process' : '/run_process';

        fetch(endpoint, {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify(processData)
        })
            .then(response => response.json())
            .then(data => {
                if (data.status === 'success') {
                    showToast(data.message, 'success');
                    // Làm mới danh sách và chọn tiến trình
                    refreshProcessList(data.process_id);
                    // Xoá các tuỳ chọn
                    clearOptions();
                    // Reset form về chế độ tạo mới
                    resetForm();
                    // Xóa trạng thái ban đầu đã lưu
                    window.originalProcessState = null;
                    // Xóa các event listener theo dõi thay đổi
                    removeChangeTracking();
                } else {
                    showToast(data.message, 'error');
                }
            })
            .catch(error => {
                console.error('Lỗi khi gửi yêu cầu:', error);
                showToast('Đã xảy ra lỗi khi kết nối với server!', 'error');
            });
    }

    function removeChangeTracking() {
        // Xóa sự kiện theo dõi thay đổi tên tiến trình
        processNameInput.removeEventListener('input', checkForChanges);

        // Các phần khác cũng có thể xóa nếu cần
        // Nhưng có thể không cần thiết vì chúng ta sẽ xóa hết các phần tử 
        // khi gọi clearOptions() hoặc khi làm mới trang
    }


    // Thêm hàm resetForm
    function resetForm() {
        runBtn.innerHTML = '<i class="fas fa-play"></i> Chạy tiến trình';
        runBtn.classList.remove('edit-mode', 'disabled-update', 'active-update');
        runBtn.dataset.editMode = '';
        runBtn.dataset.editId = '';
        runBtn.disabled = false;
        runBtn.removeAttribute('title');
    }

    /**
     * Dừng tiến trình hiện tại
     */
    function stopProcess(processId, callback) {
        if (!processId) return;

        showToast('Đang dừng tiến trình...', 'info');

        fetch('/stop_process', {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json'
            },
            body: JSON.stringify({ process_id: processId })
        })
            .then(response => response.json())
            .then(data => {
                if (data.status === 'success') {
                    showToast(data.message, 'success');
                    refreshProcessList(processId);

                    if (typeof callback === 'function') {
                        callback();
                    }
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

                // Hiển thị thông báo thành công (tùy chọn)
                showToast('Đã làm mới danh sách tiến trình', 'success');
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
        const processIds = Object.keys(processList);
        // Nếu không có tiến trình nào
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
        // Ẩn thông báo và xóa cũ
        noProcessMessage.style.display = 'none';
        processListContainer.innerHTML = '';
        // Tạo từng mục process
        processIds.forEach(id => {
            const proc = processList[id];
            const item = document.createElement('div');
            item.className = `process-item ${proc.running ? 'running' : 'stopped'}`;
            item.dataset.processId = id;
            item.innerHTML = `
            <div class="process-item-header">
                <div class="process-name">${proc.name}</div>
                <div class="process-actions">
                    <button class="btn-delete" title="Xóa">
                        <i class="fas fa-trash"></i>
                    </button>
                    <button class="btn-edit" title="Chỉnh sửa">
                        <i class="fas fa-edit"></i>
                    </button>
                    <button class="btn-restart" title="Khởi động lại">
                        <i class="fas fa-redo"></i>
                    </button>
                    <button class="btn-stop" title="Dừng" ${!proc.running ? 'disabled' : ''}>
                        <i class="fas fa-stop"></i>
                    </button>
                    <div
                        class="status-dot ${proc.running ? 'dot-running' : 'dot-stopped'}"
                        title="${proc.running ? 'Đang chạy' : 'Đã dừng'}"
                    ></div>
                </div>
            </div>
            <div class="process-details">Bắt đầu: ${proc.start_time}</div>
            <div class="process-command">${proc.command}</div>
            `;

            // Thêm event listener cho tất cả item
            item.addEventListener('click', e => {
                if (e.target.closest('.btn-edit') || e.target.closest('.btn-delete') || e.target.closest('.btn-restart') || e.target.closest('.btn-stop')) return;
                document.querySelectorAll('.process-item').forEach(el => el.classList.remove('active'));
                item.classList.add('active');
                selectProcess(id);
            });

            // Thêm event listener cho nút edit
            item.querySelector('.btn-edit').addEventListener('click', e => {
                e.stopPropagation();
                editProcess(id);
            });

            // Nút Delete
            item.querySelector('.btn-delete').addEventListener('click', e => {
                e.stopPropagation();
                if (confirm(`Bạn có chắc muốn xóa tiến trình "${proc.name}" không?`)) {
                    deleteProcess(id);
                }
            });

            // Nút Restart
            item.querySelector('.btn-restart').addEventListener('click', e => {
                e.stopPropagation();
                restartProcess(id);
            });

            // Nút Stop
            item.querySelector('.btn-stop').addEventListener('click', e => {
                e.stopPropagation();
                stopProcess(id);
            });

            processListContainer.appendChild(item);
        });

        // Chọn tiến trình mặc định
        if (selectProcessId && processList[selectProcessId]) {
            document.querySelector(`.process-item[data-process-id="${selectProcessId}"]`).classList.add('active');
            selectProcess(selectProcessId);
        } else if (!currentProcessId || !processList[currentProcessId]) {
            const firstId = processIds[0];
            document.querySelector(`.process-item[data-process-id="${firstId}"]`).classList.add('active');
            selectProcess(firstId);
        } else {
            document.querySelector(`.process-item[data-process-id="${currentProcessId}"]`).classList.add('active');
        }
    }


    /*
     * Chỉnh sửa một tiến trình
    */
    function editProcess(id) {
        // Hiển thị thông báo đang tải
        showToast('Đang tải thông tin tiến trình...', 'info');

        // Lấy thông tin chi tiết của tiến trình từ server
        fetch(`/get_process_details?process_id=${id}`)
            .then(response => response.json())
            .then(data => {
                if (data.status === 'error') {
                    showToast(data.message, 'error');
                    return;
                }

                const process = data.process;

                // Lưu trạng thái ban đầu để so sánh
                window.originalProcessState = {
                    name: process.name,
                    sources: [...process.sources],
                    options: JSON.parse(JSON.stringify(process.options))
                };

                // Xóa các nguồn và tùy chọn hiện tại
                clearOptions();

                // Điền tên tiến trình
                processNameInput.value = process.name;

                // Khôi phục các nguồn đã chọn
                if (process.sources && Array.isArray(process.sources)) {
                    selectedSources = new Set(process.sources);
                    process.sources.forEach(sourceId => {
                        const sourceItem = document.querySelector(`.source-item[data-source-id="${sourceId}"]`);
                        if (sourceItem) {
                            const checkbox = sourceItem.querySelector('input[type="checkbox"]');
                            if (checkbox) {
                                checkbox.checked = true;
                                sourceItem.classList.add('selected');
                            }
                        }
                    });
                }

                // Khôi phục các tùy chọn đã chọn
                if (process.options) {
                    Object.keys(process.options).forEach(option => {
                        // Tìm option-item tương ứng
                        const optionItem = document.querySelector(`.option-item[data-option="${option}"]`);
                        if (optionItem) {
                            const checkbox = optionItem.querySelector('input[type="checkbox"]');
                            if (checkbox) {
                                checkbox.checked = true;
                                optionItem.classList.add('selected');
                            }

                            // Xử lý đặc biệt cho option export_data với time_to_save
                            if (option === 'export_data' && process.options.time_to_save) {
                                const timeValueElement = optionItem.querySelector('.param-text');
                                if (timeValueElement) {
                                    timeValueElement.textContent = process.options.time_to_save;
                                }
                            }
                        }
                    });
                }

                // Cập nhật các tùy chọn phụ thuộc
                handleDependentOptions();

                // Cài đặt sự kiện change và click để kiểm tra thay đổi
                setupChangeTracking();

                // Cấu hình giao diện cho chế độ chỉnh sửa
                runBtn.innerHTML = 'Cập nhật';
                runBtn.classList.add('edit-mode');
                runBtn.dataset.editMode = 'edit';
                runBtn.dataset.editId = id;

                // Ban đầu, vô hiệu hóa nút cập nhật vì chưa có thay đổi
                runBtn.disabled = true;

                // Hiển thị tooltip hoặc thông báo
                runBtn.setAttribute('title', 'Không có thay đổi để cập nhật');

                // Cuộn lên trên để người dùng thấy form
                // Ưu tiên các selector khác nhau
                const scrollElement = document.getElementById('control') ||
                    document.querySelector('.process-control') ||
                    document.querySelector('.process-list');

                if (scrollElement) {
                    scrollElement.scrollIntoView({ behavior: 'smooth' });
                }

                // Hiển thị thông báo
                showToast('Đang chỉnh sửa tiến trình: ' + process.name, 'info');
            })
            .catch(error => {
                console.error('Lỗi khi lấy thông tin tiến trình:', error);
                showToast('Không thể tải thông tin tiến trình', 'error');
            });
    }

    /**
     * Kiểm tra xem có thay đổi nào trong các tùy chọn hay không
     */
    function setupChangeTracking() {
        // Theo dõi sự thay đổi tên tiến trình
        processNameInput.addEventListener('input', checkForChanges);

        // Theo dõi sự thay đổi các nguồn
        document.querySelectorAll('.source-item').forEach(item => {
            item.addEventListener('click', checkForChanges);
        });

        // Theo dõi sự thay đổi các tùy chọn
        document.querySelectorAll('.option-item').forEach(item => {
            item.addEventListener('click', checkForChanges);
            // Theo dõi cả khi thay đổi giá trị tham số (như time_to_save)
            const paramText = item.querySelector('.param-text');
            if (paramText) {
                // Sử dụng MutationObserver để theo dõi thay đổi nội dung
                const observer = new MutationObserver(checkForChanges);
                observer.observe(paramText, { characterData: true, childList: true, subtree: true });
            }
        });

        // Kích hoạt kiểm tra ban đầu
        checkForChanges();
    }

    function checkForChanges() {
        if (!window.originalProcessState) return;

        // 1. Kiểm tra tên
        const nameChanged = processNameInput.value !== window.originalProcessState.name;

        // 2. Kiểm tra nguồn dữ liệu
        const currentSources = Array.from(selectedSources);
        const sourcesChanged = !arraysEqual(currentSources, window.originalProcessState.sources);

        // 3. Kiểm tra tùy chọn
        const currentOptions = getCurrentOptions();
        const optionsChanged = !objectsEqual(currentOptions, window.originalProcessState.options);

        // Kích hoạt nút nếu có bất kỳ thay đổi nào
        const hasChanges = nameChanged || sourcesChanged || optionsChanged;

        if (hasChanges) {
            // Kích hoạt nút và áp dụng kiểu cho nút đã kích hoạt
            runBtn.disabled = false;
            runBtn.removeAttribute('title');
            runBtn.classList.remove('disabled-update');
            runBtn.classList.add('active-update');  // Thêm class mới
        } else {
            // Vô hiệu hóa nút
            runBtn.disabled = true;
            runBtn.setAttribute('title', 'Không có thay đổi để cập nhật');
            runBtn.classList.add('disabled-update');
            runBtn.classList.remove('active-update');  // Xóa class
        }
    }

    // Hàm hỗ trợ để lấy tùy chọn hiện tại
    function getCurrentOptions() {
        const options = {};
        document.querySelectorAll('.option-item').forEach(item => {
            const cb = item.querySelector('input[type="checkbox"]');
            if (!cb || !cb.checked || item.classList.contains('disabled')) return;

            const opt = item.dataset.option;
            if (opt === 'export_data') {
                options.export_data = true;
                const n = parseInt(
                    item.querySelector('.param-text').textContent,
                    10
                ) || 0;
                options.time_to_save = n;
            } else {
                options[opt] = true;
            }
        });
        return options;
    }

    // Hàm so sánh mảng
    function arraysEqual(a, b) {
        if (a.length !== b.length) return false;
        return a.every((val, idx) => val === b[idx]);
    }

    // Hàm so sánh đối tượng
    function objectsEqual(obj1, obj2) {
        const keys1 = Object.keys(obj1);
        const keys2 = Object.keys(obj2);

        if (keys1.length !== keys2.length) return false;

        return keys1.every(key => {
            if (typeof obj1[key] === 'object' && typeof obj2[key] === 'object') {
                return objectsEqual(obj1[key], obj2[key]);
            }
            return obj1[key] === obj2[key];
        });
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
     * Chuyển đổi mã ANSI thành HTML có màu sắc - phiên bản cải tiến
     * Xử lý cả escape sequence \u001b và [32m
     */
    function convertAnsiToHtml(text) {
        if (!text) return '';

        // Bảng màu ANSI cơ bản
        const colors = {
            '30': 'black',
            '31': 'red',
            '32': 'green',
            '33': 'yellow',
            '34': 'blue',
            '35': 'magenta',
            '36': 'cyan',
            '37': 'white',
            '90': 'gray',
            '91': 'lightred',
            '92': 'lightgreen',
            '93': 'lightyellow',
            '94': 'lightblue',
            '95': 'lightmagenta',
            '96': 'lightcyan',
            '97': 'white'
        };

        // Lớp CSS tương ứng với các màu ANSI
        const colorClasses = {
            'black': 'ansi-black',
            'red': 'ansi-red',
            'green': 'ansi-green',
            'yellow': 'ansi-yellow',
            'blue': 'ansi-blue',
            'magenta': 'ansi-magenta',
            'cyan': 'ansi-cyan',
            'white': 'ansi-white',
            'gray': 'ansi-gray',
            'lightred': 'ansi-lightred',
            'lightgreen': 'ansi-lightgreen',
            'lightyellow': 'ansi-lightyellow',
            'lightblue': 'ansi-lightblue',
            'lightmagenta': 'ansi-lightmagenta',
            'lightcyan': 'ansi-lightcyan'
        };

        try {
            // Xử lý hết các ký tự escape sequence
            let result = text;

            // Bước 1: Thay thế các escape sequence \u001b[XXm
            // \u001b là ký tự escape trong ANSI
            result = result.replace(/\u001b\[(\d+)m/g, '[$1m');

            // Bước 2: Xóa hoàn toàn mã reset [0m để tránh cản trở việc phân tích
            result = result.replace(/\[0m/g, '');

            // Bước 3: Xử lý các mã màu [XXm còn lại
            for (const [code, color] of Object.entries(colors)) {
                const pattern = new RegExp(`\\[${code}m`, 'g');
                result = result.replace(pattern, `<span class="${colorClasses[color]}">`);
            }

            // Bước 4: Đóng tất cả các thẻ span mở
            result = result + '</span>';

            // Nếu không có thay đổi nào, trả về text gốc đã escape
            if (result === text + '</span>') {
                return escapeHtml(text);
            }

            return result;
        } catch (error) {
            console.error("Lỗi khi xử lý ANSI:", error);
            return escapeHtml(text);
        }
    }

    /**
     * Escape HTML để tránh XSS
     */
    function escapeHtml(unsafe) {
        if (!unsafe) return '';
        return unsafe
            .replace(/&/g, "&amp;")
            .replace(/</g, "&lt;")
            .replace(/>/g, "&gt;")
            .replace(/"/g, "&quot;")
            .replace(/'/g, "&#039;");
    }

    // Thêm sự kiện scroll để biết người dùng đã cuộn hay chưa
    document.addEventListener('DOMContentLoaded', function () {
        const terminal = document.getElementById('terminal');

        terminal.addEventListener('scroll', function () {
            // Nếu user cuộn lên (không ở cuối cùng), đánh dấu là đã cuộn
            const isAtBottom = terminal.scrollHeight - terminal.scrollTop <= terminal.clientHeight + 50;
            userScrolled = !isAtBottom;
        });
    });

    /**
     * Cập nhật output trong terminal
     */
    let previousOutputLength = 0;
    function updateTerminalOutput() {
        if (!currentProcessId) return;

        fetch(`/get_process_status?process_id=${currentProcessId}`)
            .then(response => response.json())
            .then(data => {
                if (data.status === 'error') {
                    terminal.innerHTML = `<p class="terminal-line">${escapeHtml(data.message)}</p>`;
                    clearInterval(statusCheckInterval);
                    return;
                }

                // Cập nhật UI
                stopBtn.disabled = !data.running;
                processStatusIndicator.style.display = data.running ? 'inline-block' : 'none';

                // Cập nhật trạng thái trong processList
                if (processList[currentProcessId]) {
                    processList[currentProcessId].running = data.running;
                }

                // 3) Cập nhật chấm màu ở danh sách
                const item = document.querySelector(`.process-item[data-process-id="${currentProcessId}"]`);
                if (item) {
                    // Cập nhật class
                    item.classList.toggle('running', data.running);
                    item.classList.toggle('stopped', !data.running);

                    // Cập nhật status-dot
                    const dot = item.querySelector('.status-dot');
                    if (dot) {
                        dot.className = 'status-dot ' + (data.running ? 'dot-running' : 'dot-stopped');
                    }

                    // Cập nhật trạng thái nút dừng
                    const stopBtn = item.querySelector('.btn-stop');
                    if (stopBtn) {
                        stopBtn.disabled = !data.running;
                    }
                }

                // Kiểm tra xem terminal có ở cuối cùng hay không trước khi cập nhật nội dung
                const isAtBottom = terminal.scrollHeight - terminal.scrollTop <= terminal.clientHeight + 50;

                // Cập nhật output
                if (data.output && data.output.length > 0) {
                    terminal.innerHTML = '';
                    data.output.forEach(line => {
                        const lineElement = document.createElement('p');
                        lineElement.className = 'terminal-line';

                        // Sử dụng innerHTML với hàm chuyển đổi ANSI, không dùng textContent
                        lineElement.innerHTML = convertAnsiToHtml(line);

                        terminal.appendChild(lineElement);
                    });

                    // Chỉ tự động cuộn xuống nếu người dùng chưa cuộn lên hoặc đang ở cuối
                    if (!userScrolled || isAtBottom) {
                        terminal.scrollTop = terminal.scrollHeight;
                    }
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


    function deleteProcess(processId) {
        fetch('/delete_process', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ process_id: processId })
        })
            .then(r => r.json())
            .then(data => {
                if (data.status === 'success') {
                    showToast(data.message, 'success');
                    refreshProcessList();
                } else {
                    showToast(data.message, 'error');
                }
            })
            .catch(() => showToast('Lỗi khi xóa tiến trình', 'error'));
    }

    function restartProcess(processId) {
        showToast('Đang restart...', 'info');

        fetch('/restart_process', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ process_id: processId })
        })
            .then(r => r.json())
            .then(data => {
                if (data.status === 'success') {
                    showToast(data.message, 'success');
                    refreshProcessList(processId);
                } else {
                    showToast(data.message, 'error');
                }
            })
            .catch(() => showToast('Lỗi khi gọi restart', 'error'));
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