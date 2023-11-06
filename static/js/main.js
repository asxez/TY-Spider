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
            for (const arr of arrs) {
                let data = arr.substring(1) + "}";
                if (data.includes("title") && data.includes("href")) {
                    /*
                    * 使用正则表达式提取数据（因为得到的数据是单引号，无法用JSON解析，使用正则也是无奈之举（不要问为什么不把单引号转成双引号））
                    */
                    const word = /'word':\s*'([^']+)'/i.exec(data);
                    const description = /'description':\s*'([^']+)'/i.exec(data);
                    const href = /'href':\s*'([^']+)'/i.exec(data);
                    const title = /'title':\s*'([^']+)'/i.exec(data);
                    if (title && href) {
                        console.log(word);
                        console.log(description);
                        console.log(href);
                        console.log(title);
                    }
                }
            }
        }
    }
    xhr.open('POST', 'http://127.0.0.1:1314/search/', true)
    xhr.send(fd);
});
