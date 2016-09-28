function loadComments(pId) {
	var post = document.getElementById("post_" + String(pId));
	if (post.getElementsByClassName('post_comments').length > 0) {
		post.removeChild(post.getElementsByClassName('post_comments')[0])
		return false;
	}
	function showComments(comments) {
		var post_comments = document.createElement('div');
		post_comments.setAttribute('class', 'post_comments');
		var comment_list = document.createElement('dl');
		for (i = 0; i < comments.length; i++) {
			// FIXME: rewrite concisely
			var comment_author = document.createElement('dt');
			if (! comments[i][6]) {
				author_name = 'anonymous';
			} else {
				author_name = comments[i][6];
			}
			comment_author.appendChild(document.createTextNode(author_name));
			comment_list.appendChild(comment_author);
			var comment_body = document.createElement('dd');
			comment_body.appendChild(document.createTextNode(comments[i][3]));
			comment_list.appendChild(comment_body);
			// console.log(comments[i][3]);
		}
		post_comments.appendChild(comment_list);
		post.appendChild(post_comments);
	}
	var xmlhttp = new XMLHttpRequest();
	var url = String(pId) + "/get_comments";
	xmlhttp.onreadystatechange = function() {
		if (this.readyState == 4 && this.status == 200) {
			var comments = JSON.parse(this.responseText).comments;
			showComments(comments);
		}
	};
	xmlhttp.open("GET", url, true);
	xmlhttp.send();
}

function loadCommentForm(pId) {
	var post = document.getElementById("post_" + String(pId));
	// FIXME: this should be done by calling getElementsByName
	if (post.getElementsByTagName('form').length > 0) {
		post.removeChild(post.getElementsByTagName('form')[0])
		return false;
	}
	var xmlhttp = new XMLHttpRequest();
	var url = String(pId) + "/new";
	xmlhttp.onreadystatechange = function() {
		if (this.readyState == 4 && this.status == 200) {
			var parser = new DOMParser();
			var doc = parser.parseFromString(this.responseText, 'text/html');
			document.getElementById('post_' + String(pId)).appendChild(doc.getElementsByName('new_comment_form')[0]);
		}
	};
	xmlhttp.open("GET", url, true);
	xmlhttp.send();
}
