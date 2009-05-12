var book_data = null;
var show = "all";

var BookShelf = Class.extend({
    init: function(){
        //		return this._super();
    },
    
    not_to_be_shown: function(book){
        if (show == "all") 
            return false;
        if (show == "tech" && book.is_tech) 
            return false;
        if (show == "non-tech" && (!book.is_tech)) 
            return false;
        return true;
    },
    
    borrower: function(book){
        return (available(book) ? "" : book.borrowed_by);
    },
	
    render: function(){
    },
    
    return_link: function(book, link_text){
        return '<a href="/return/' + book.key + '">'+ link_text +'</a>';
    },
    
    addBook: function(){
    },
    
    removeBook: function(){
    }
});
/**********************************************************************************/
var MyBooks = BookShelf.extend({

    init: function(){
        return this._super();
    },
    
    empty: function(){
        $("#my_table").empty();
    },
    
    render_header: function(){
        $("#my_table").append('<thead><tr><th class="colone"></th><th class="coltwo">Book</th><th class="colthree">Lent to</th><th class="colfour"></th></tr></thead><tbody id="my_table_body"><tr/></tbody>');
    },
    
    render: function(books){
        myBooks.empty();
        if (books) {
            myBooks.render_header();
            $.each(books, this.mybookrow);
        }
        else {
            $("#my_table").append('<tr class="nothing"><td>Nothing yet. Use the lookup box above to start adding to your collection.</td></tr>');
        }
    },
    
    addBook: function(){
    },
    
    removeBook: function(){
    },
    
    del_link: function(book){
        return '<a href="/delete/' + book.key + '">delete</a>';
    },
    
    lend_link: function(book){
        return '<a href="/lend/' + book.key + '">lend</a>';
    },
    
    mybookrow: function(i){
        myBooks.newRow(this);
    },
    
    borrower: function(book){
		result = this._super(book);
		if(result != ""){
			result += "  " + this.return_link(book, "x");
		}
		return result;
    },
    
    newRow: function(book){
        if (myBooks.not_to_be_shown(this)) //crappy hack for *this*
            return;
        if ($("#my_table tr.nothing").length > 0) {
            myBooks.empty();
            myBooks.render_header();
        }
        $("#my_table_body tr:first").before("<tr><td>" + myBooks.del_link(book) + "</td><td>" + book.title +
        " by " +
        book.author +
        "</td><td>" +
        myBooks.borrower(book) +
        "</td><td class='action'>" +
        myBooks.lend_link(book) +
        "</td></tr>");
    },
    lent_count: function(list){
        count = 0;
        if (list) {
            $.each(list, function(i){
                if (!available(this)) 
                    count++;
            });
        }
        return count;
    },
    
    handle_event: function(event, book){
        if (event == "evt_book_added") {
            myBooks.newRow(book);
        }
    }
});
/**********************************************************************************/
var BorrowedBooks = BookShelf.extend({
    init: function(){
        return this._super();
    },
    
    render: function(books){
        $("#borrowed_table").empty();
        if (books) {
            $("#borrowed_table").append('<tr><th class="colone">From</th><th class="coltwo">Book</th><th class="colthree"></th><th class="colfour"></th></tr>');
            $.each(books, this.borrowedBookrow);
        }
        else {
            $("#borrowed_table").append('<tr class="nothing"><td>Nothing yet. Don&apos;t you want to read any of the books below?</td></tr>');
        }
    },
    
    addBook: function(){
    },
    
    removeBook: function(){
    },
    
    borrowedBookrow: function(i){
        if (borrowedBooks.not_to_be_shown(this)) 
            return;
        $("#borrowed_table").append("<tr><td>" + this.owner + "</td><td>" + this.title + " by " +
        this.author +
        "</td><td></td><td class='action'>" +
        borrowedBooks.return_link(this, "return") +
        "</td></tr>");
    }
});
/**********************************************************************************/
var OtherBooks = BookShelf.extend({
    init: function(){
        return this._super();
    },
    
    render: function(books){
        $("#others_table").empty();
        if (books.length > 0) {
            $("#others_table").append('<tr><th class="colone">Owner</th><th class="coltwo">Book</th><th class="colthree">Lent to</th><th class="colfour"></th></tr>');
            $.each(books, this.othersbookrow);
        }
        else {
            $("#others_table").append('<tr class="nothing"><td>Nothing here? That can&apos;t be true!</td></tr>');
        }
    },
    
    addBook: function(){
    },
    
    removeBook: function(){
    },
    
    borrow_link: function(book){
        return available(book) ? '<a href="/borrow/' + book.key + '">borrow</a>' : "";
    },
    
    othersbookrow: function(i){
        if (otherBooks.not_to_be_shown(this)) 
            return;
        $("#others_table").append("<tr><td>" + this.owner + "</td><td>" + this.title + " by " +
        this.author +
        "</td><td>" +
        otherBooks.borrower(this) +
        "</td><td class='action'>" +
        otherBooks.borrow_link(this) +
        "</td></tr>");
    }
});
/**********************************************************************************/
var Mediator = Class.extend({
    registry: {},
    
    init: function(){
        return this._super();
    },
    trigger: function(event, data){
    
    },
    register: function(event, callback){
        list = registry[event];
        if (!list) {
            list = new Array();
            registry[event] = list;
        }
        list.push(callback);
    }
});
/**********************************************************************************/
function showgif(){

    //script from: http://www.sitepoint.com/forums/showthread.php?t=581377
    // loading.gif from http://www.ajaxload.info/
    
    $('<div id="overlay"/>').css({
        position: 'fixed',
        top: 0,
        left: 0,
        width: '100%',
        height: $(window).height() + 'px',
        background: 'white url(/s/loading.gif) no-repeat center'
    }).appendTo('body');
}

function updateBookCount(data){
    $("#book_count").empty();
    own_count = data.mybooks ? data.mybooks.length : 0
    borrow_count = data.borrowedBooks ? data.borrowedBooks.length : 0
    $("#book_count").append("Overall summary of your books: <big class='bignum'> " + own_count + "</big> owned, <big class='bignum'>" +
    myBooks.lent_count(data.mybooks) +
    "</big> lent, <big class='bignum'>" +
    borrow_count +
    "</big> borrowed.");
}

function available(book){
    return (book.borrowed_by == "None");
}

function renderBooks(data){
    book_data = data;
    updateBookCount(data);
    myBooks.render(data.mybooks);
    borrowedBooks.render(data.borrowedBooks);
    otherBooks.render(data.others);
    $('#overlay').hide();
}

function show_tech_only(){
    show = "tech";
    renderBooks(book_data);
}

function show_non_tech_only(){
    show = "non-tech";
    renderBooks(book_data);
}

function show_all(){
    show = "all";
    renderBooks(book_data);
}

function fetch_books(){
    showgif();
    $.getJSON("/mybooksj", renderBooks);
    $("#tech_only").click(show_tech_only);
    $("#non_tech_only").click(show_non_tech_only);
    $("#show_all").click(show_all);
}

function on_add(book){
    myBooks.newRow(book);
    if (!book_data['mybooks']) {
        book_data['mybooks'] = [];
    }
    book_data['mybooks'].push(book);
    updateBookCount(book_data);
    $("#book_title").val("");
    $("#book_author").val("");
    $("#suggestbox").focus();
}

function on_add_error(xhr, desc, exceptionobj){
    alert(xhr.statusText);
}

function post_new_book(title, author, asin){
    $("#suggestbox").val("");
    $.ajax({
        url: "/addBook",
        type: "POST",
        data: {
            "book_title": title,
            "book_author": author,
            "book_asin": asin
        },
        success: on_add,
        error: on_add_error,
        dataType: "json"
    });
}

function setup_handlers(){
    var options = {
        script: "/lookup_amz?",
        varname: "fragment",
        json: true,
        callback: function(obj){
            post_new_book(obj.value, obj.info, obj.id);
        }
    };
    new bsn.AutoSuggest('suggestbox', options);
    
    $("#btn_add_book").click(function(){
        post_new_book($("#book_title").val(), $("#book_author").val(), 0);
    });
    
    $("#edit_nick").click(function(){
        $(this).hide();
        $("#nick_text").show().focus();
    });
    
    $("#nick_text").keypress(function(e){
        c = e.which ? e.which : e.keyCode;
        if (c == 13) {
            nickname = jQuery(this).val();
            this.blur();
            $.ajax({
                url: "/nickname",
                type: "POST",
                data: {
                    "new_nick": nickname
                },
                success: function(msg){
                    $("#nick_text").hide();
                    $("#hi_msg").text("Hi " + nickname);
                },
                error: function(xhr){
                    alert(xhr.statusText);
                }
            });
        }
    });
    
    $(document).keypress(function(e){
        c = e.which ? e.which : e.keyCode;
        if (c == 97) {
            $("#suggestbox").focus();
        }
    });
}

var myBooks = new MyBooks();
var borrowedBooks = new BorrowedBooks();
var otherBooks = new OtherBooks();

$(document).ready(function(){
    $("#nick_text").hide();
    $("#manual").hide();
    $("#suggestbox").focus();
    
    $("#show_manual").click(function(){
        $(this).hide();
        $("#manual").show();
        $("#book_title").focus();
    });
    fetch_books();
    setup_handlers();
});
