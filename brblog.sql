--
-- TODO: postDate should be called entryData
---

drop view  if exists PostFull;
drop view  if exists CommentFull;
drop table if exists Comment;
drop table if exists Post;
drop table if exists Entry;

-- Don't forget to
-- pragma foreign_keys = ON;

create table Entry (
    eId         integer  primary key autoincrement,
    title       text,
    body        text     not null,
    postDate    datetime not null,
    isVisible   boolean  not null
);

-- No autoincrement for pId because it's ok reuse the id's of the post that
-- had been deleted.  Not so with eId's.
create table Post (
    eId         integer,
    pId         integer primary key,
    foreign key (eId) references Entry (eId) on delete cascade
);

create table Comment (
    eId         integer,
    pId         integer,
    cId         integer,
    author      text,
    mark        text,
    primary key (pId, cId),
    foreign key (eId) references Entry (eId) on delete cascade,
    foreign key (pId) references Post  (pId) on delete cascade
);

create view PostFull as
    select pId, title, body, postDate, isVisible
    from Post, Entry
    where Entry.eId = Post.eId;

create view CommentFull as
    select pId, cId, title, body, postDate, isVisible, author, mark
    from Comment, Entry
    where Entry.eId = Comment.eId;

-- create trigger AdjustEntryTime
    -- after insert on Entry
    -- for each row
    -- begin
        -- update Entry
        -- set postDate = datetime(New.postDate, 'localtime')
        -- where eId = New.eId;
    -- end;

create trigger CommentFullDelete 
    instead of delete on CommentFull
    for each row
    begin
        delete from Comment
        where Comment.pId = Old.pId
        and   Comment.cId = Old.cId;
    end;

create trigger PostFullDelete 
    instead of delete on PostFull
    for each row
    begin
        delete from Post
        where Post.pId = Old.pId;
    end;

create trigger CommentFullInsert
    instead of insert on CommentFull
    for each row
    begin
        insert into Entry values (
            null,
            New.title,
            New.body,
            New.postDate,
            New.isVisible
        );
        insert into Comment values (
            (select max(eId) from Entry),
            New.pId,
            New.cId,
            New.author,
            New.mark
        );
    end;

create trigger PostFullInsert
    instead of insert on PostFull
    for each row
    begin
        insert into Entry values (
            null,
            New.title,
            New.body,
            New.postDate,
            New.isVisible
        );
        insert into Post values (
            (select max(eId) from Entry),
            New.pId
        );
    end;

create trigger CommentFullUpdate
    instead of update on CommentFull
    for each row
    begin
        update Entry
        set title       = New.title,
            body        = New.body,
            postDate    = New.postDate,
            isVisible   = New.isVisible
        where eId = (select eId from Comment where pId = New.pId
                                             and   cId = New.cId);
        update Comment
        set pId         = New.pId,
            cId         = New.cId,
            author      = New.author,
            mark        = New.mark
        where eId = (select eId from Comment where pId = New.pId
                                             and   cId = New.cId);
    end;

create trigger PostFullUpdate
    instead of update on PostFull
    for each row
    begin
        update Entry
        set title       = New.title,
            body        = New.body,
            postDate    = New.postDate,
            isVisible   = New.isVisible
        where eId = (select eId from Post where pId = New.pId);
        update Post
        set pId         = New.pId
        where pId = New.pId;
    end;

-- Reference tree looks like this:
-- eId  1   2
--      ^   ^
--      |   |
-- pId  1   |
--      ^   |
--       \ / 
-- cId    1
--
-- So when a post is deleted, all comments that reference it get deleted
-- automatically as well ('on delete cascade'); but we also have to manually
-- delete entries that are referenced *by* the post and by all the comments we
-- have deleted.  This sort of referential integrity is done by the triggers
-- below.  Hola!  SQL rules.

create trigger CleanCommentEntries
    after delete on Comment
    for each row
    begin
        delete from Entry where eId = old.eId;
    end;

create trigger CleanPostEntries
    after delete on Post
    for each row
    begin
        delete from Entry where eId = old.eId;
    end;

-- insert into Entry values (null, 'first post', 'hello, world!', datetime('now'), 1);
-- insert into Post values ((select max(eId) from Entry), null);

-- insert into Entry values (null, 'comment on the first post', 'nice posting...', datetime('now'), 1);
-- insert into Comment values (
    -- (select max(eId) from Entry),
    -- (select max(pId) from Post),
    -- ifnull((select max(cId) from Comment) + 1, 1),
    -- 'xio',
    -- null
-- );

-- insert into PostFull values (null, 'second post!', 'hi again', datetime('now'), 0);
-- insert into PostFull values (null, 'already the third', 'so hej,<br>using some tags this time', datetime('now'), 1);

-- insert into CommentFull values (2, 1, '2nd comment on the second posting', 'hola mate', datetime('now'), 0, 'stranger', null);
-- insert into CommentFull values (2, 2, 'actual second comment', 'Vote for Edinaya Rossia!', datetime('now'), 0, 'Rossijanin', 'idiot');
