document.addEventListener('DOMContentLoaded', () => {
    // Cấu hình API
    // const API_BASE_URL = 'http://localhost:5543'; // Thay đổi URL này nếu API chạy ở port/host khác

    // Các biến cục bộ
    let currentProcessId = null;
    let taskList = {};
    let statusCheckInterval;
    let selectedCameras = new Set();
    let userScrolled = false;

    // Các phần tử DOM
    const camerasContainer = document.getElementById('sources-container');
    const roomSelect = document.getElementById('room-select');
    const runBtn = document.getElementById('run-btn');
    const stopBtn = document.getElementById('stop-btn');
    const clearBtn = document.getElementById('clear-btn');
    const refreshBtn = document.getElementById('refresh-btn');
    const processListContainer = document.getElementById('process-list-container');
    const noProcessMessage = document.getElementById('no-process-message');
    const terminal = document.getElementById('terminal');
    const taskNameInput = document.getElementById('process-name');
    const currentTaskName = document.getElementById('current-process-name');
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
        loadAvailableCameras();
        loadAvailableRooms();
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
        // Nút chạy task
        runBtn.addEventListener('click', () => {
            // Chế độ tạo task mới bình thường
            startProcess();
        });

        // Nút dừng task
        stopBtn.addEventListener('click', stopProcess);

        // Nút làm mới danh sách task
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
     * Tải danh sách các phòng có trong hệ thống từ API
     */
    function loadAvailableRooms() {
        fetch("/get_available_rooms")
            .then(response => response.json())
            .then(rooms => {
                roomSelect.innerHTML = `
              <option value="">Tất cả</option>
            `;

                rooms.forEach(roomId => {
                    const option = document.createElement("option");
                    option.value = roomId;
                    option.textContent = roomId;
                    roomSelect.appendChild(option);
                });
            })
            .catch(error => {
                console.error("Lỗi khi tải danh sách phòng:", error);
                roomSelect.innerHTML = `
              <option disabled selected>Không thể tải phòng</option>
            `;
            });
    }

    /**
     * Tải danh sách nguồn dữ liệu có sẵn từ API
     */

    function loadAvailableCameras() {
        fetch('/get_available_cameras')
            .then(response => response.json())
            .then(sources => {
                camerasContainer.innerHTML = '';

                sources.forEach(source => {
                    const sourceItem = document.createElement('div');
                    sourceItem.className = 'source-item';
                    sourceItem.dataset.sourceId = source.camera_id;

                    sourceItem.innerHTML = `
                            <input type="checkbox" id="source-${source.camera_id}" value="${source.camera_id}">
                            <label for="source-${source.camera_id}">${source.name}</label>
                        `;

                    // Lấy checkbox
                    const cb = sourceItem.querySelector('input[type="checkbox"]');

                    // Xử lý sự kiện click trên source-item
                    sourceItem.addEventListener('click', e => {
                        // Nếu click vào checkbox hoặc label, để hành vi mặc định xảy ra
                        if (e.target === cb || e.target.tagName === 'LABEL') {
                            return;
                        }
                        // Toggle checkbox khi click vào khoảng trống trong source-item
                        cb.checked = !cb.checked;
                        // Cập nhật UI và selectedCameras
                        sourceItem.classList.toggle('selected', cb.checked);
                        if (cb.checked) {
                            selectedCameras.add(source.camera_id);
                        } else {
                            selectedCameras.delete(source.camera_id);
                        }
                    });

                    // Xử lý sự kiện change trên checkbox để đồng bộ UI
                    cb.addEventListener('change', () => {
                        sourceItem.classList.toggle('selected', cb.checked);
                        if (cb.checked) {
                            selectedCameras.add(source.camera_id);
                        } else {
                            selectedCameras.delete(source.camera_id);
                        }
                    });

                    camerasContainer.appendChild(sourceItem);
                });
            })
            .catch(error => {
                console.error('Lỗi khi tải nguồn dữ liệu:', error);
                camerasContainer.innerHTML = '<p style="white-space: nowrap;">Không thể tải nguồn dữ liệu. Vui lòng thử lại sau.</p>';
            });
    }


    /**
     * Bắt đầu task mới
     */
    function startProcess() {
        // Kiểm tra xem đang trong chế độ chỉnh sửa hay không
        const isEditMode = runBtn.dataset.editMode === 'edit';
        const editId = runBtn.dataset.editId;


        // 1. Kiểm tra xem đã nhập tên task chưa
        if (!taskNameInput.value.trim()) {
            showToast('Vui lòng nhập tên cho task!', 'error');
            return;
        }

        // 2. Kiểm tra xem đã chọn nguồn dữ liệu chưa
        if (selectedCameras.size === 0) {
            showToast('Vui lòng chọn ít nhất một nguồn dữ liệu!', 'error');
            return;
        }

        // 3. Lấy phòng được chọn
        const selectedRoom = roomSelect.value;

        // 4. Thu thập các tùy chọn
        const features = {};
        document.querySelectorAll('.option-item').forEach(item => {
            const cb = item.querySelector('input[type="checkbox"]');
            if (!cb || !cb.checked || item.classList.contains('disabled')) return;

            const opt = item.dataset.option;
            if (opt === 'export_data') {
                // ghi nhận bật export_data...
                features.export_data = true;
                // ...và thêm time_to_save với giá trị n
                const n = parseInt(
                    item.querySelector('.param-text').textContent,
                    10
                ) || 0;
                features.time_to_save = n;
            } else {
                // các option bình thường
                features[opt] = true;
            }
        });

        // 5. Xây payload
        const processData = {
            task_name: taskNameInput.value.trim(),
            camera_ids: Array.from(selectedCameras),
            features: features,
            room_id: selectedRoom || null
        };

        // Nếu là chế độ edit, thêm task_id vào payload
        if (isEditMode && editId) {
            processData.task_id = editId;
        }

        // 5. Thông báo đang gửi
        showToast(`Đang ${isEditMode ? 'cập nhật' : 'bắt đầu'} task...`, 'info');

        // 6. Gửi request lên server
        const endpoint = isEditMode ? '/update_task' : '/run_task';

        fetch(endpoint, {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify(processData)
        })
            .then(response => response.json())
            .then(data => {
                if (data.status === 'success') {
                    showToast(data.message, 'success');
                    // Làm mới danh sách và chọn task
                    refreshProcessList(data.task_id);
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
        // Xóa sự kiện theo dõi thay đổi tên task
        taskNameInput.removeEventListener('input', checkForChanges);

        // Các phần khác cũng có thể xóa nếu cần
        // Nhưng có thể không cần thiết vì chúng ta sẽ xóa hết các phần tử 
        // khi gọi clearOptions() hoặc khi làm mới trang
    }


    // Thêm hàm resetForm
    function resetForm() {
        runBtn.innerHTML = '<i class="fas fa-play"></i> Chạy task';
        runBtn.classList.remove('edit-mode', 'disabled-update', 'active-update');
        runBtn.dataset.editMode = '';
        runBtn.dataset.editId = '';
        runBtn.disabled = false;
        runBtn.removeAttribute('title');
    }

    /**
     * Dừng task hiện tại
     */
    function stopProcess(taskId, callback) {
        if (!taskId) return;

        showToast('Đang dừng task...', 'info');

        fetch('/stop_task', {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json'
            },
            body: JSON.stringify({ task_id: taskId })
        })
            .then(response => response.json())
            .then(data => {
                if (data.status === 'success') {
                    showToast(data.message, 'success');
                    refreshProcessList(taskId);

                    if (typeof callback === 'function') {
                        callback();
                    }
                } else {
                    showToast(data.message, 'error');
                }
            })
            .catch(error => {
                console.error('Lỗi khi dừng task:', error);
                showToast('Đã xảy ra lỗi khi kết nối với server!', 'error');
            });
    }


    /**
     * Làm mới danh sách task
     */
    function refreshProcessList(selectTaskId = null) {
        fetch('/get_all_task_ids')
            .then(response => response.json())
            .then(data => {
                taskList = data;
                updateProcessListUI(selectTaskId);

                // Hiển thị thông báo thành công (tùy chọn)
                showToast('Đã làm mới danh sách task', 'success');
            })
            .catch(error => {
                console.error('Lỗi khi tải danh sách task:', error);
                showToast('Không thể tải danh sách task', 'error');
            });
    }

    function formatFeatures(features) {
        return Object.entries(features)
            .map(([key, value]) => `${key}: ${value}`)
            .join(', ');
    }

    /**
     * Cập nhật giao diện danh sách task
     */
    function updateProcessListUI(selectProcessId = null) {
        const processIds = Object.keys(taskList);
        // Nếu không có task nào
        if (processIds.length === 0) {
            processListContainer.innerHTML = '';
            noProcessMessage.style.display = 'block';
            terminal.innerHTML = '<p class="terminal-line">Chưa có task nào được chạy.</p>';
            currentProcessId = null;
            currentTaskName.textContent = 'Đầu ra task';
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
            const proc = taskList[id];
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
            <div class="process-command">${formatFeatures(proc.features)}</div>
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
                editTask(id);
            });

            // Nút Delete
            item.querySelector('.btn-delete').addEventListener('click', e => {
                e.stopPropagation();
                if (confirm(`Bạn có chắc muốn xóa task "${proc.name}" không?`)) {
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

        // Chọn task mặc định
        if (selectProcessId && taskList[selectProcessId]) {
            document.querySelector(`.process-item[data-process-id="${selectProcessId}"]`).classList.add('active');
            selectProcess(selectProcessId);
        } else if (!currentProcessId || !taskList[currentProcessId]) {
            const firstId = processIds[0];
            document.querySelector(`.process-item[data-process-id="${firstId}"]`).classList.add('active');
            selectProcess(firstId);
        } else {
            document.querySelector(`.process-item[data-process-id="${currentProcessId}"]`).classList.add('active');
        }
    }


    /*
     * Chỉnh sửa một task
    */
    function editTask(id) {
        // Hiển thị toast đang tải
        showToast('Đang tải thông tin task...', 'info');

        fetch(`/get_task_details?task_id=${id}`)
            .then(res => res.json())
            .then(data => {
                if (data.status === 'error') {
                    showToast(data.message, 'error');
                    return;
                }

                // Lấy config từ payload
                const cfg = data.config;
                if (!cfg) {
                    showToast('Server trả về thiếu config', 'error');
                    return;
                }

                // Chuẩn hóa các trường
                const taskName = cfg.name || id;
                const roomId = cfg.room_id ?? '';
                const cameraIds = Array.isArray(cfg.camera_ids) ? cfg.camera_ids : [];
                const features = (cfg.features && typeof cfg.features === 'object')
                    ? cfg.features : {};

                // Lưu state gốc
                window.originalProcessState = {
                    name: taskName,
                    room_id: roomId,
                    camera_ids: [...cameraIds],
                    features: JSON.parse(JSON.stringify(features))
                };

                // Reset UI trước khi fill lại
                clearOptions();
                taskNameInput.value = taskName;
                roomSelect.value = roomId;

                // Khôi phục danh sách camera (sources)
                selectedCameras = new Set(cameraIds);
                cameraIds.forEach(cam => {
                    const item = document.querySelector(`.source-item[data-source-id="${cam}"]`);
                    if (!item) return;
                    const cb = item.querySelector('input[type="checkbox"]');
                    cb.checked = true;
                    item.classList.add('selected');
                });

                // Khôi phục các feature đã chọn
                Object.keys(features).forEach(feat => {
                    const item = document.querySelector(`.option-item[data-option="${feat}"]`);
                    if (!item) return;
                    const cb = item.querySelector('input[type="checkbox"]');
                    cb.checked = true;
                    item.classList.add('selected');

                    // Nếu có time_to_save thì show giá trị
                    if (feat === 'export_data' && features.time_to_save != null) {
                        const txt = item.querySelector('.param-text');
                        if (txt) txt.textContent = features.time_to_save;
                    }
                });

                // Cập nhật các tùy chọn phụ thuộc và tracking
                handleDependentOptions();
                setupChangeTracking();

                // Chuyển nút Run → Cập nhật
                runBtn.innerHTML = 'Cập nhật';
                runBtn.classList.add('edit-mode');
                runBtn.dataset.editMode = 'edit';
                runBtn.dataset.editId = id;
                runBtn.disabled = true;
                runBtn.title = 'Không có thay đổi để cập nhật';

                // Scroll form vào view
                const scrollEl = document.getElementById('control')
                    || document.querySelector('.process-control')
                    || document.querySelector('.process-list');
                if (scrollEl) scrollEl.scrollIntoView({ behavior: 'smooth' });

                showToast('Đang chỉnh sửa task: ' + taskName, 'info');
            })
            .catch(err => {
                console.error('Lỗi khi lấy thông tin task:', err);
                showToast('Không thể tải thông tin task', 'error');
            });
    }


    /**
     * Kiểm tra xem có thay đổi nào trong các tùy chọn hay không
     */
    function setupChangeTracking() {
        // Theo dõi sự thay đổi tên task
        taskNameInput.addEventListener('input', checkForChanges);

        // Theo dõi
        roomSelect.addEventListener('change', checkForChanges);

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
        const nameChanged = taskNameInput.value !== window.originalProcessState.name;

        // 2. Kiểm tra room_id
        const roomChanged = roomSelect.value !== (window.originalProcessState.room_id ?? '');

        // 2. Kiểm tra camera_ids
        const currentSources = Array.from(selectedCameras);
        const sourcesChanged = !arraysEqual(
            currentSources,
            window.originalProcessState.camera_ids   // <-- sửa ở đây
        );

        // 3. Kiểm tra features
        const currentFeatures = getCurrentOptions(); // giả sử trả về object { face_recognition: true, ... }
        const featuresChanged = !objectsEqual(
            currentFeatures,
            window.originalProcessState.features     // <-- và ở đây
        );

        const hasChanges = nameChanged || roomChanged || sourcesChanged || featuresChanged;

        if (hasChanges) {
            runBtn.disabled = false;
            runBtn.removeAttribute('title');
            runBtn.classList.remove('disabled-update');
            runBtn.classList.add('active-update');
        } else {
            runBtn.disabled = true;
            runBtn.setAttribute('title', 'Không có thay đổi để cập nhật');
            runBtn.classList.add('disabled-update');
            runBtn.classList.remove('active-update');
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
     * Chọn một task để xem
     */
    function selectProcess(processId) {
        // Đặt task hiện tại
        currentProcessId = processId;

        // Cập nhật UI
        const process = taskList[processId];
        if (process) {
            currentTaskName.textContent = process.name;
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
    function updateTerminalOutput() {
        if (!currentProcessId) return;

        fetch(`/get_task_status?task_id=${currentProcessId}`)
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
                if (taskList[currentProcessId]) {
                    taskList[currentProcessId].running = data.running;
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

                // Nếu task đã dừng, dừng kiểm tra trạng thái
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
        selectedCameras.clear();
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

        // Reset tên task
        taskNameInput.value = '';

        // Reset roomSelect về "Tất cả các phòng"
        if (roomSelect) {
            roomSelect.value = '';
        }

        // Chạy lại logic phụ thuộc (face_emotion, raise_hand, ...)
        handleDependentOptions();

        // Thông báo
        showToast('Đã xóa tất cả tùy chọn!', 'success');
    }


    function deleteProcess(processId) {
        fetch('/delete_task', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ task_id: processId })
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
            .catch(() => showToast('Lỗi khi xóa task', 'error'));
    }

    function restartProcess(processId) {
        // Lưu tham chiếu đến toast thông báo đang xử lý
        const processingToastId = showToastWithId('Đang restart...', 'info');

        fetch('/restart_task', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ task_id: processId })
        })
            .then(r => r.json())
            .then(data => {
                // Đóng toast "đang xử lý" trước khi hiển thị kết quả mới
                closeToast(processingToastId);

                if (data.status === 'success') {
                    showToast(data.message, 'success');
                    refreshProcessList(processId);
                } else {
                    showToast(data.message, 'error');
                }
            })
            .catch(() => {
                // Đóng toast "đang xử lý" trước khi hiển thị lỗi
                closeToast(processingToastId);
                showToast('Lỗi khi gọi restart', 'error');
            });
    }

    // Phiên bản mở rộng của showToast trả về ID để có thể đóng nó sau
    function showToastWithId(message, type = 'info', duration = null) {
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

        // Tạo ID duy nhất cho toast
        const toastId = 'toast-' + Date.now();
        toast.id = toastId;

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

        // Chỉ tự động ẩn nếu duration được chỉ định
        if (duration !== null) {
            setTimeout(() => {
                closeToast(toastId);
            }, duration);
        }

        return toastId;
    }

    // Hàm đóng toast theo ID
    function closeToast(toastId) {
        const toast = document.getElementById(toastId);
        if (toast) {
            toast.style.animation = 'fadeOut 0.3s';
            toast.addEventListener('animationend', () => {
                toast.remove();
                // Xóa container nếu không còn toast
                const toastContainer = document.querySelector('.toast-container');
                if (toastContainer && toastContainer.children.length === 0) {
                    toastContainer.remove();
                }
            });
        }
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