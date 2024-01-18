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

let button = document.getElementById('ty-btn');
let search = document.getElementById('input-search');

button.addEventListener('click', () => {
    let xhr = new XMLHttpRequest();
    let fd = new FormData();
    fd.append('q', search.value);
    xhr.onreadystatechange = function () {
        if (this.readyState === 4 && this.status === 200) {
            let res = JSON.parse(this.responseText)['response']
            let arrs = res.slice(1, -1).split('}');
            let contentArray = [];
            for (const arr of arrs) {
                let data = arr.substring(1) + "}";
                if (data.includes("title") && data.includes("href")) {
                    const word = /'keywords':\s*'([^']+)'/i.exec(data);
                    const href = /'href':\s*'([^']+)'/i.exec(data);
                    const title = /'title':\s*'([^']+)'/i.exec(data);
                    if (title && href && word) {
                        let contents = {
                            TTitle: title[1],
                            THref: href[1],
                            TKeywords: word[1]
                        };
                        const exists = contentArray.some(obj => JSON.stringify(obj) === JSON.stringify(contents));
                        if (exists)
                            continue;
                        contentArray.push(contents);
                    }
                }
            }
            window.sessionStorage.setItem("content", JSON.stringify(contentArray.slice(0, 200)));
            window.sessionStorage.setItem("search", search.value);
            window.open("http://127.0.0.1:1314/show/")
        }
    }
    xhr.open('POST', 'http://127.0.0.1:1314/search/', true)
    xhr.send(fd);
});
