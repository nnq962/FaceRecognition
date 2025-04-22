from answer_sender import send_answers_to_server

# Đáp án của một lớp/phòng
answers = {
    "student1": "A",
    "student2": "F",
    "student3": "E"
}

# Gửi đáp án - ID phòng có thể là bất kỳ chuỗi nào
result = send_answers_to_server(
    answers=answers,
    room_id="AI",  # Bạn có thể dùng bất kỳ ID nào
    server_address="http://192.168.1.64:3000"
)
print(result)