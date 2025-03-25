from flask import Flask, render_template

app = Flask(__name__)

@app.route("/")
def home():
    return render_template("attendance_status.html")

@app.route("/users")
def users():
    return render_template("users.html")

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5555)
