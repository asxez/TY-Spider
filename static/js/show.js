function init() {
    let contents = JSON.parse(window.sessionStorage.getItem("content"));
    let DTitle = window.sessionStorage.getItem("search");
    let left = document.getElementById("left");
    document.title = DTitle + " - 天眼搜索";

    for (const TContent of contents.slice(0, 10)) {

        let title = document.createElement("div");
        title.className = "title";
        let href = document.createElement("div");
        href.className = "href";
        let keywords = document.createElement("div");
        keywords.className = "keywords";

        let title1 = document.createElement("div");
        title1.className = "title-text";
        title1.textContent = TContent["TTitle"];
        title.appendChild(title1);

        let href1 = document.createElement("div");
        href1.className = "href-text";
        href1.textContent = TContent["THref"];
        href.appendChild(href1);

        let keywordsText = document.createElement("div");
        keywordsText.className = "keywords-text";
        keywordsText.textContent = TContent["TKeywords"];
        keywords.appendChild(keywordsText);

        let a = document.createElement("a");
        a.target = "_blank";
        a.href = TContent["THref"];

        let content = document.createElement("div");
        content.className = "content";
        content.appendChild(href);
        content.appendChild(title);
        content.appendChild(keywords);

        a.appendChild(content);
        left.appendChild(a);
    }
}

function makePageButton() {
    let contents = JSON.parse(window.sessionStorage.getItem("content"));
    let len = contents.length;
    let page = len / 10;
    if (len / 10 > 10) {
        page = 10;
    }
    for (let i = 1; i <= page; i++) {
        let footer = document.getElementById("footer");
        let button = document.createElement("div");
        button.className = "text";
        button.textContent = `${i}`;
        footer.appendChild(button);
    }
    let button = document.getElementsByClassName("text");
    for (let i = 0; i < page; i++) {
        button[i].addEventListener("click", () => {
            gotoPage(i * 10, i * 10 + 10);
        });
    }
}

window.addEventListener("load", () => {
    init();
    makePageButton();
});

function gotoPage(pageStart, pageEnd) {
    let contents = JSON.parse(window.sessionStorage.getItem("content"));
    let left = document.getElementById("left");
    left.innerHTML = "";

    for (let TContent of contents.slice(pageStart, pageEnd)) {

        let title = document.createElement("div");
        title.className = "title";
        let href = document.createElement("div");
        href.className = "href";
        let keywords = document.createElement("div");
        keywords.className = "keywords";

        let title1 = document.createElement("div");
        title1.className = "title-text";
        title1.textContent = TContent["TTitle"];
        title.appendChild(title1);

        let href1 = document.createElement("div");
        href1.className = "href-text";
        href1.textContent = TContent["THref"];
        href.appendChild(href1);

        let keywordsText = document.createElement("div");
        keywordsText.className = "keywords-text";
        keywordsText.textContent = TContent["TKeywords"];
        keywords.appendChild(keywordsText);

        let a = document.createElement("a");
        a.target = "_blank";
        a.href = TContent["THref"];

        let content = document.createElement("div");
        content.className = "content";
        content.appendChild(href);
        content.appendChild(title);
        content.appendChild(keywords);

        a.appendChild(content);
        left.appendChild(a);
    }
}
