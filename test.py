from flask import Flask, render_template

app = Flask(__name__)

def is_small_diff(a: str, b: str) -> bool:
    """ Kiểm tra nếu hai từ chỉ khác nhau 1 ký tự """
    if a == b:
        return False
    if abs(len(a) - len(b)) == 1:
        if len(a) < len(b) and b.startswith(a):
            return True
        if len(b) < len(a) and a.startswith(b):
            return True
    if len(a) == len(b) and a[:-1] == b[:-1]:
        return True
    return False

def refine_word(real_word: str, matched_word: str) -> str:
    """ Bôi đỏ phần sai trong một từ gần đúng """
    output = []
    min_len = min(len(real_word), len(matched_word))
    for i in range(min_len):
        if real_word[i] == matched_word[i]:
            output.append(matched_word[i])
        else:
            output.append(f'<span class="highlight-red">{matched_word[i]}</span>')
    if len(matched_word) < len(real_word):
        missing = real_word[len(matched_word):]
        output.append(f'<span class="highlight-red">{missing}</span>')
    elif len(matched_word) > len(real_word):
        extra = matched_word[len(real_word):]
        output.append(f'<span class="highlight-red">{extra}</span>')
    return "".join(output)

def highlight_extra_syllables(real_transcripts_ipa: str, matched_transcripts_ipa: str) -> str:
    """ Bôi vàng các âm tiết thừa. """
    real_syllables = real_transcripts_ipa.split()
    matched_syllables = matched_transcripts_ipa.split()

    formatted_output = []
    real_index = 0
    len_real = len(real_syllables)

    for matched_syllable in matched_syllables:
        if real_index < len_real and matched_syllable == real_syllables[real_index]:
            formatted_output.append(matched_syllable)
            real_index += 1
        elif real_index < len_real and is_small_diff(matched_syllable, real_syllables[real_index]):
            formatted_output.append(matched_syllable)
            real_index += 1
        elif matched_syllable in real_syllables[real_index:]:
            formatted_output.append(matched_syllable)
            real_index = real_syllables.index(matched_syllable, real_index) + 1
        else:
            formatted_output.append(f'<span class="highlight-yellow">{matched_syllable}</span>')

    return " ".join(formatted_output)

def refine_word_for_yellow(real_word: str, matched_word: str) -> str:
    """
    So sánh từng ký tự của matched_word với real_word:
    - Nếu một ký tự bị **thêm**, bôi vàng nó.
    - Nếu một ký tự bị **thiếu**, bôi đỏ nó.
    """
    output = []
    min_len = min(len(real_word), len(matched_word))

    # So sánh ký tự theo từng phần
    for i in range(min_len):
        if real_word[i] == matched_word[i]:
            output.append(matched_word[i])
        else:
            output.append(f'<span class="highlight-yellow">{matched_word[i]}</span>')

    # Nếu matched_word **ngắn hơn**, có ký tự thiếu -> bôi đỏ ký tự bị thiếu
    if len(matched_word) < len(real_word):
        missing = real_word[len(matched_word):]
        output.append(f'<span class="highlight-red">{missing}</span>')

    # Nếu matched_word **dài hơn**, có ký tự thừa -> bôi vàng ký tự bị thêm
    elif len(matched_word) > len(real_word):
        extra = matched_word[len(real_word):]
        output.append(f'<span class="highlight-yellow">{extra}</span>')

    return "".join(output)


import re

def refine_yellow_highlights(real_transcripts_ipa: str, highlighted: str) -> str:
    """
    Xử lý lại kết quả của highlight_extra_syllables:
    - Nếu từ đó gần giống với một từ trong real IPA, chỉ bôi vàng hoặc đỏ phần sai.
    - Nếu là thừa hoàn toàn, giữ nguyên bôi vàng.
    """
    real_syllables = real_transcripts_ipa.split()
    
    # Tách token để kiểm tra từng từ đang được bôi vàng
    tokens = highlighted.split()
    
    refined_tokens = []
    real_index = 0
    
    for token in tokens:
        # Kiểm tra xem token có bị bôi vàng không
        match = re.match(r'<span class="highlight-yellow">(.*?)</span>', token)
        if match:
            raw_token = match.group(1)  # Lấy từ thực tế mà không có thẻ span

            # Nếu còn từ trong real IPA để so sánh
            if real_index < len(real_syllables):
                real_word = real_syllables[real_index]

                if is_small_diff(raw_token, real_word):
                    # Nếu gần giống, bôi màu chính xác
                    refined_tokens.append(refine_word_for_yellow(real_word, raw_token))
                    real_index += 1  # Chuyển sang từ tiếp theo
                else:
                    # Nếu không phải lỗi nhỏ, giữ nguyên bôi vàng
                    refined_tokens.append(token)
            else:
                # Nếu không còn từ trong real IPA để đối chiếu, giữ nguyên bôi vàng
                refined_tokens.append(token)
        else:
            # Nếu token không bôi vàng, giữ nguyên
            refined_tokens.append(token)
            if real_index < len(real_syllables):
                real_index += 1  # Chuyển sang từ tiếp theo nếu có

    final_refined = " ".join(refined_tokens)
    return final_refined

@app.route("/")
def home():
    real_transcripts_ipa = "haʊ ˈmɛni bəˈnænəz ɔn ðə ˈteɪbəl?"
    matched_transcripts_ipa = "haʊ ˈmɛni bəˈnnænə ˈhæpi nu jɪr ɔn ðə ˈteɪbəl?"

    # Bước 1: Tìm các âm tiết bị bôi vàng
    highlighted_ipa = highlight_extra_syllables(real_transcripts_ipa, matched_transcripts_ipa)

    # Bước 2: Xử lý lại âm tiết bôi vàng
    refined_ipa = refine_yellow_highlights(real_transcripts_ipa, highlighted_ipa)

    return render_template(
        "result.html",
        real_transcripts_ipa=real_transcripts_ipa,
        matched_transcripts_ipa=matched_transcripts_ipa,
        highlighted_ipa=refined_ipa
    )

if __name__ == "__main__":
    app.run(debug=True)