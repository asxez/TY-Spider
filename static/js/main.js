function nowtime() {
    let date = new Date();
    let time = document.getElementById('now_time');
    let hours = date.getHours();
    let min = date.getMinutes();
    if (min < 10) {
        time.innerHTML = `${hours}:0${min}`;
    } else {
        time.innerHTML = `${hours}:${min}`;
    }
}

setInterval(nowtime, 1000);

function sjyy() {
    let xhr = new XMLHttpRequest();
    xhr.onreadystatechange = function () {
        if (this.readyState === 4 && this.status === 200) {
            let res = JSON.parse(this.responseText);
            document.getElementById('text').textContent = res['hitokoto'];
        }
    }
    xhr.open("GET", "https://v1.hitokoto.cn", true);
    xhr.send();
}

document.addEventListener('DOMContentLoaded', sjyy);
