/* global jQuery */

var state = {};

var lastDims = {};
var tableWidgets = [];
var shipImages = [];

var canvas$;
var g2x;
var leaderboard$;


function repaint(init) {
    if (init) {
        canvas$ = $("#gameCanvas");
        g2x = canvas$[0].getContext("2d");
        leaderboard$ = $("#leaderboard");
        canvas$.attr("width", 1024);
        canvas$.attr("height", 1024);
    }


    var widthRatio = 1024.0 / state.width;
    var heightRatio = 1024.0 / state.height;

    g2x.clearRect(0, 0, state.width, state.height);

    var pmines = {};
    state.mines.forEach(function(mine) {
        if (pmines[mine.owner]) {
            pmines[mine.owner]++;
        } else {
            pmines[mine.owner]=1;
        }
    });

    var pmap = {};
    if (tableWidgets.length !== state.players.length) {

        leaderboard$.empty();
        var table = $("<table style='width: 100%' ><th colspan='3' style='color: white; text-align: left'>Player</th><th style='color: white; text-align: right'>Score</th></table>");
        leaderboard$.append(table);

        tableWidgets = [];
        var i = 1;
        state.players.sort(function (a, b) {
            return b.score - a.score;
        }).forEach(function (player) {
            var rowWidgets = [];
            tableWidgets.push(rowWidgets);

            pmap[player.name] = player;
            var tr = $("<tr style='width:100%'/>");
            if (i % 2) {
                tr.css("background-color", "#202020");
            }

            table.append(tr);
            var td = $("<td style='text-align: left; width: 12px' />");
            tr.append(td);
            var img = $("<img src='ship" + (player.id % 60) + ".png' style='width: 12px; height: 12px' />");
            td.append(img);
            rowWidgets.push(img);

            table.append(tr);
            td = $("<td style='text-align: center'; width: 14px />");
            tr.append(td);
            var label = $("<label style='color:orange; font: monospace'/>");
            td.append(label);
            label.text(pmines[player.name] ? fill(pmines[player.name],2,'0') : "00");
            rowWidgets.push(label);

            table.append(tr);
            td = $("<td style='text-align: left' />");
            tr.append(td);
            var label = $("<label style='color:orange; font: monospace'/>");
            td.append(label);
            label.text(player.name);
            rowWidgets.push(label);


            var td = $("<td style='text-align: right' />");
            tr.append(td);
            var label = $("<label style='color:orange; font: monospace'/>");
            td.append(label);
            label.text(player.score);
            rowWidgets.push(label);

            i++;
        });
    } else {
        var tempPlayers = state.players.sort(function (a, b) {
            return b.score - a.score;
        });
        for (var i = 0; i < tempPlayers.length; i++) {
            tableWidgets[i][0].attr("src", 'ship' + (tempPlayers[i].id % 60) + '.png');
            tableWidgets[i][1].text(pmines[state.players[i].name] ? fill(pmines[state.players[i].name],2,'0') : "00");
            tableWidgets[i][2].text(tempPlayers[i].name);
            tableWidgets[i][3].text(tempPlayers[i].score);
            pmap[state.players[i].name] = tempPlayers[i];
        }
    }

    var stroke = Math.min(state.width, state.height) / 1024;

    g2x.strokeStyle = "#FFFFFF";
    g2x.lineWidth = 1;

    state.wormholes.forEach(function (wormhole) {
        g2x.fillStyle = "#660066";
        g2x.beginPath();
        g2x.arc(wormhole.px * widthRatio, wormhole.py * heightRatio, wormhole.radius * (widthRatio + heightRatio) / 2, 0, Math.PI * 2);
        g2x.fill();
    });

    state.mines.forEach(function (mine) {
        if (pmap[mine.owner]) {
            g2x.drawImage(shipImages[pmap[mine.owner].id % 60], mine.px * widthRatio - stroke * 1, mine.py * heightRatio - stroke * 1, stroke * 2, stroke * 2);
        }

        g2x.beginPath();
        g2x.arc(mine.px * widthRatio, mine.py * heightRatio, stroke * .4, 0, Math.PI * 2);
        g2x.stroke();
    });

    state.bombs.forEach(function (bomb) {
        if (bomb.delay - 5 < bomb.life) {
            console.log("pbig");
            g2x.fillStyle = "#FF0000";
            g2x.beginPath();
            g2x.arc(bomb.px * widthRatio, bomb.py * heightRatio, state.bombRadius * Math.max(widthRatio, heightRatio), 0, Math.PI * 2);
            g2x.fill();
        } else {
            console.log("psmall", bomb.delay, bomb.life);
            g2x.fillStyle = "#FFFF00";
            g2x.beginPath();
            g2x.arc(bomb.px * widthRatio, bomb.py * heightRatio, stroke * .6, 0, Math.PI * 2);
            g2x.fill();
        }
        
    });


    state.players.forEach(function (player) {
        g2x.translate(player.px * widthRatio, player.py * heightRatio);
        g2x.rotate(Math.atan2(player.vy, player.vx) + Math.PI / 2);
        g2x.drawImage(shipImages[player.id % 60], -stroke * 1.2, -stroke * 1.2, stroke * 2.4, stroke * 2.4);
        g2x.setTransform(1, 0, 0, 1, 0, 0);
    });

    function fill(inp, len, char) {
        inp += "";
        while (inp.length < len) {
            inp = char + inp;
        }
        return inp;
    }
    var secondsLeft = Math.floor((state.totalTicks - state.tick) / (1000 / state.tickDelay));
    $("#timestamp").text(fill(Math.floor((secondsLeft / 3600) % 100), 2, "0") + ":" + fill(Math.floor((secondsLeft / 60) % 60), 2, "0") + ":" + fill(Math.floor(secondsLeft % 60), 2, "0"));
}

$(document).ready(function () {
    for (var i = 0; i < 60; i++) {
        var img = new Image();
        img.src = "ship" + i + ".png";
        shipImages.push(img);
    }

    var init = true;
    var ws = new WebSocket("ws://codebb.cloudapp.net:17427");
    ws.onopen = function (evt) {
        console.log(evt);
    };
    ws.onmessage = function (evt) {
        //console.log(evt);
        state = JSON.parse(evt.data);


        //console.log(state);
        repaint(init);
        if (init) {
            init = false;
        }
        ws.send('frame');
    };

});
