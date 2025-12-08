
// Darkmode
// document.getElementById('toggle').addEventListener('change', () => {
//     const body = document.body;
//     const toggle = document.getElementById('toggle');
//     body.classList.toggle('dark-theme', toggle.checked);
//     document.getElementById('modeLabel').textContent = toggle.checked ? 'Dark Mode' : 'Light Mode';
// });


const input = document.getElementById('search');
const tagsListSearched = []
const allPossibleTags = new Set();
const allImages = [];
const ALL_TAG = 'All Stickers';


// Llenar el div de id=catalogue con las fotos de la carpeta "procesadas_jpg"
function loadImages() {
    // Cargar data.csv, que tiene formato "path,tags;tags" con D3
    d3.csv('data.csv', d3.autoType).then(data => {
        let id = 0;
        data.forEach(d => {
            // Convertir los tags a un array y eliminar espacios en blanco
            d.tags = d.tags.split(';').map(tag => tag.trim().toLowerCase());
            // Añadir los tags a la lista de todos los posibles tags
            d.tags.forEach(tag => allPossibleTags.add(tag));
            d.id = id++;
            allImages.push(d);

            // Autocomplete para el buscador según los tags en allPossibleTags
        });
        // sort allPossibleTags
        const allPossibleTagsOrdered = Array.from(new Set(Array.from(allPossibleTags).sort()));
        allPossibleTagsOrdered.unshift(ALL_TAG);
        autocomplete(document.getElementById('search'), allPossibleTagsOrdered);


        d3.select('#catalogue')
            .selectAll('div')
            .data(allImages.slice(0, 10), d => d.id)
            .join('div')
            .attr('class', 'item')
            .append('img')
            .attr('src', d => './procesadas_jpg/' + d.nombre)
            .attr('alt', 'Imagen')
            .attr('class', 'item');
    })
}
function searchTags(tag) {
    // Verificar si el tag ya está en la lista de tags buscados
    input.value = ''; // Limpiar el input después de agregar el tag

    if (tagsListSearched.includes(tag)) {
        // Si el tag ya está en la lista, no hacer nada
        return;
    }
    // Crear un nuevo span para el tag
    const tagsList = document.getElementById('tagsList');
    const tagSpan = document.createElement('span');
    tagSpan.textContent = tag;
    tagSpan.className = 'tag';
    // Añadir el nuevo span al DOM
    tagsList.appendChild(tagSpan);

    tagSpan.addEventListener('click', () => {
        // Eliminar el tag de la lista de tags buscados
        tagsListSearched.splice(tagsListSearched.indexOf(tag), 1);
        // Eliminar el span del DOM
        tagsList.removeChild(tagSpan);
        // Mostrar todas las imágenes
        filterImagesByTags();
    });


    tagsListSearched.push(tag);
    filterImagesByTags()

}

function filterImagesByTags() {
    if (tagsListSearched.length === 0) {
        // Si no hay tags buscados, mostrar todas las imágenes
        d3.select('#catalogue')
            .selectAll('div')
            .classed('hidden', false);
        return;
    }
    let filteredImages;
    if (tagsListSearched.includes(ALL_TAG.toLowerCase())) {
        filteredImages = allImages;
    }
    else{
        filteredImages = allImages.filter(d => {
            let found = false;
            tagsListSearched.forEach(t => {
                if (d.tags.includes(t)) {
                    found = true;
                }
            });
            return found;
        })
    }

    console.log(filteredImages)
    // Actualizar el catálogo con las imágenes filtradas
    d3.select('#catalogue')
        .selectAll('div')
        .data(filteredImages, d => d.id)
        .join(
            enter => {
                let enterDivs = enter.append('div');
                enterDivs.attr('class', 'item');
                enterDivs.append('img')
                    .attr('src', d => './procesadas_jpg/' + d.nombre)
                    .attr('alt', 'Imagen')
                    .attr('class', 'item');
                return enterDivs;
            },
            update => update,
            exit => exit.classed('hidden', true)
        )
}

input.addEventListener('keydown', (event) => {
    if (event.key === 'Enter') {
        event.preventDefault();
        const tag = input.value.trim().toLowerCase();
        if (tag.length > 0) {
            searchTags(tag);
        }
    }
});

// document.getElementById('addTagButton').addEventListener('click', () => {
//     const tag = input.value.trim().toLowerCase();
//     if (tag.length > 0) {
//         searchTags(tag);
//     }
// });

document.addEventListener('DOMContentLoaded', loadImages);


// Autocomplete function
function autocomplete(inp, arr) {
    /*the autocomplete function takes two arguments,
    the text field element and an array of possible autocompleted values:*/
    var currentFocus;
    /*execute a function when someone writes in the text field:*/
    inp.addEventListener("click", function (e) {
        var a, b, i, val = this.value;
        currentFocus = -1;
        /*create a DIV element that will contain the items (values):*/
        a = document.createElement("DIV");
        a.setAttribute("id", this.id + "autocomplete-list");
        a.setAttribute("class", "autocomplete-items");
        /*append the DIV element as a child of the autocomplete container:*/
        this.parentNode.appendChild(a);
        /*for each item in the array...*/
        for (i = 0; i < arr.length; i++) {
            /*check if the item starts with the same letters as the text field value:*/
            // check if arr contain val.toUpperCase()
            if (val.length == 0 || arr[i].toUpperCase().includes(val.toUpperCase())) {
                /*create a DIV element for each matching element:*/
                b = document.createElement("DIV");
                /*make the matching letters bold:*/
                b.innerHTML = arr[i];
                /*insert a input field that will hold the current array item's value:*/
                b.innerHTML += "<input type='hidden' value='" + arr[i] + "'>";
                /*execute a function when someone clicks on the item value (DIV element):*/
                b.addEventListener("click", function (e) {
                    /*insert the value for the autocomplete text field:*/
                    inp.value = this.getElementsByTagName("input")[0].value;
                    /*close the list of autocompleted values,
                    (or any other open lists of autocompleted values:*/
                    closeAllLists();
                    searchTags(inp.value.trim().toLowerCase());
                });
                a.appendChild(b);
            }
        }
    })
    inp.addEventListener("input", function (e) {
        var a, b, i, val = this.value;
        /*close any already open lists of autocompleted values*/
        closeAllLists();
        // if (!val) { return false; }
        currentFocus = -1;
        /*create a DIV element that will contain the items (values):*/
        a = document.createElement("DIV");
        a.setAttribute("id", this.id + "autocomplete-list");
        a.setAttribute("class", "autocomplete-items");
        /*append the DIV element as a child of the autocomplete container:*/
        this.parentNode.appendChild(a);
        /*for each item in the array...*/
        for (i = 0; i < arr.length; i++) {
            /*check if the item starts with the same letters as the text field value:*/
            // check if arr contain val.toUpperCase()
            if (val.length == 0 || arr[i].toUpperCase().includes(val.toUpperCase())) {
                /*create a DIV element for each matching element:*/
                b = document.createElement("DIV");
                /*make the matching letters bold:*/
                // Identificar la zona que coincide con el valor, que puede estar en cualquiera parte
                // y ponerla en rojo
                var regex = new RegExp(val, 'i'); // 'i' for case-insensitive                
                b.innerHTML = arr[i].replace(regex, "<strong style='color: black;'>" + val + "</strong>");
                /*insert a input field that will hold the current array item's value:*/
                b.innerHTML += "<input type='hidden' value='" + arr[i] + "'>";
                /*execute a function when someone clicks on the item value (DIV element):*/
                b.addEventListener("click", function (e) {
                    /*insert the value for the autocomplete text field:*/
                    inp.value = this.getElementsByTagName("input")[0].value;
                    /*close the list of autocompleted values,
                    (or any other open lists of autocompleted values:*/
                    closeAllLists();
                    searchTags(inp.value.trim().toLowerCase());
                });
                a.appendChild(b);
            }
        }
    });
    /*execute a function presses a key on the keyboard:*/
    inp.addEventListener("keydown", function (e) {
        var x = document.getElementById(this.id + "autocomplete-list");
        if (x) x = x.getElementsByTagName("div");
        if (e.keyCode == 40) {
            /*If the arrow DOWN key is pressed,
            increase the currentFocus variable:*/
            currentFocus++;
            /*and and make the current item more visible:*/
            addActive(x);
        } else if (e.keyCode == 38) { //up
            /*If the arrow UP key is pressed,
            decrease the currentFocus variable:*/
            currentFocus--;
            /*and and make the current item more visible:*/
            addActive(x);
        } else if (e.keyCode == 13) {
            /*If the ENTER key is pressed, prevent the form from being submitted,*/
            e.preventDefault();
            if (currentFocus > -1) {
                /*and simulate a click on the "active" item:*/
                if (x) x[currentFocus].click();
            }
        }
    });
    function addActive(x) {
        /*a function to classify an item as "active":*/
        if (!x) return false;
        /*start by removing the "active" class on all items:*/
        removeActive(x);
        if (currentFocus >= x.length) currentFocus = 0;
        if (currentFocus < 0) currentFocus = (x.length - 1);
        /*add class "autocomplete-active":*/
        x[currentFocus].classList.add("autocomplete-active");
    }
    function removeActive(x) {
        /*a function to remove the "active" class from all autocomplete items:*/
        for (var i = 0; i < x.length; i++) {
            x[i].classList.remove("autocomplete-active");
        }
    }
    function closeAllLists(elmnt) {
        /*close all autocomplete lists in the document,
        except the one passed as an argument:*/
        var x = document.getElementsByClassName("autocomplete-items");
        for (var i = 0; i < x.length; i++) {
            if (elmnt != x[i] && elmnt != inp) {
                x[i].parentNode.removeChild(x[i]);
            }
        }
    }
    /*execute a function when someone clicks in the document:*/
    document.addEventListener("click", function (e) {
        closeAllLists(e.target);
    });
}