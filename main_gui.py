import tkinter as tk
from tkinter import filedialog
from tkinter import messagebox
from tkinter import ttk
from tkinter import Menu
from ttkthemes.themed_style import ThemedStyle

import os
import shutil
import getpass
import platform
import json
import datetime
import requests

import metadata_w


# metadata, repo connections, submit

class Application(tk.Frame):
    def __init__(self, master=None):
        super().__init__(master)
        self.grid_columnconfigure(0, weight=1)
        self.input_dir = ''
        self.output_dir = ''
        self.metadata = []
        self.non_empties = []

        self.dcterms = ['dc.contributor.advisor', 'dc.contributor.author', 'dc.contributor.editor',
                        'dc.contributor.illustrator', 'dc.contributor.other', 'dc.contributor', 'dc.coverage.spatial',
                        'dc.coverage.temporal', 'dc.creator', 'dc.date.accessioned', 'dc.date.available',
                        'dc.date.copyright', 'dc.date.created', 'dc.date.issued', 'dc.date.submitted',
                        'dc.date.updated', 'dc.date', 'dc.description.abstract', 'dc.description.provenance',
                        'dc.description.sponsorship', 'dc.description.statementofresponsibility',
                        'dc.description.tableofcontents', 'dc.description.uri', 'dc.description.version',
                        'dc.description', 'dc.format.extent', 'dc.format.medium', 'dc.format.mimetype', 'dc.format',
                        'dc.identifier.citation', 'dc.identifier.govdoc', 'dc.identifier.isbn', 'dc.identifier.ismn',
                        'dc.identifier.issn', 'dc.identifier.other', 'dc.identifier.sici', 'dc.identifier.slug',
                        'dc.identifier.uri', 'dc.identifier', 'dc.language.iso', 'dc.language.rfc3066', 'dc.language',
                        'dc.provenance', 'dc.publisher', 'dc.relation.haspart', 'dc.relation.hasversion',
                        'dc.relation.isbasedon', 'dc.relation.isformatof', 'dc.relation.ispartof',
                        'dc.relation.ispartofseries', 'dc.relation.isreferencedby', 'dc.relation.isreplacedby',
                        'dc.relation.isversionof', 'dc.relation.replaces', 'dc.relation.requires', 'dc.relation.uri',
                        'dc.relation', 'dc.rights.holder', 'dc.rights.license', 'dc.rights.uri', 'dc.rights',
                        'dc.source.uri', 'dc.source', 'dc.subject.classification', 'dc.subject.ddc', 'dc.subject.lcc',
                        'dc.subject.lcsh', 'dc.subject.mesh', 'dc.subject.other', 'dc.subject', 'dc.title.alternative',
                        'dc.title', 'dc.type']
        
        self.row_count = 0
        self.main_label_width = 16
        self.main_label_font = ('Arial', 14)
        self.main_input_font = ('Arial', 12)
        self.y_pad = 8
        
        self.create_menu()
        self.create_widgets()

    @staticmethod
    def login(host, user, passwd):
        try:
            response = requests.post(host + '/users/' + user + '/login',
                                     data={'password': passwd, 'expiring': False})
        except requests.ConnectionError as e:
            raise Exception("Unable to connect to ArchivesSpace server: " + str(e))

        try:
            output = response.json()
        except Exception:
            print
            response.content
            raise Exception(
                "ArchivesSpace server responded with status {}, but returned a non-JSON document".format(
                    response.status_code))

        if 'error' in output:
            raise Exception(
                "Unable to log into ArchivesSpace installation; message from server: {}".format(output['error']))
        else:
            token = output['session']

        session = requests.Session()
        session.headers.update({'X-ArchivesSpace-Session': token})
        return session

    @staticmethod
    def request(host, method, url, params, expected_response, data=None):
        if not url.startswith('/'):
            url = '/' + url
        #print(host + url)
        response = method(host + url, params=params, data=data)
        if response.status_code != expected_response:
            print('Response code: %s', response.status_code)
            print('Response body: %s', response.text)
            # raise Exception(response.status_code, response)

        try:
            output = response.json()
        except Exception:
            raise Exception("ArchivesSpace server responded with status {}, but returned a non-JSON document".format(
                response.status_code))

        if 'error' in output:
            raise Exception(output['error'])

        # print(json.dumps(response.json(), indent=4, sort_keys=True))

        return response

    def donothing(self):
        pass

    def create_menu(self):
        menubar = Menu(root)
        filemenu = Menu(menubar, tearoff=0)
        filemenu.add_command(label="New", command=self.donothing)
        filemenu.add_command(label="Open", command=self.donothing)
        filemenu.add_command(label="Save", command=self.donothing)
        filemenu.add_command(label="Save as...", command=self.donothing)
        filemenu.add_command(label="Close", command=self.donothing)
        filemenu.add_separator()

        filemenu.add_command(label="Exit", command=root.quit)
        menubar.add_cascade(label="File", menu=filemenu)

        helpmenu = Menu(menubar, tearoff=0)
        helpmenu.add_command(label="Help Index", command=self.donothing)
        helpmenu.add_command(label="About...", command=self.donothing)
        menubar.add_cascade(label="Help", menu=helpmenu)

        root.config(menu=menubar)

    def create_label_entry(self, parent_obj, text, column=0, row=0, tv=''):
        ttk.Label(parent_obj, text=text,  # background='gray',
                 width=self.main_label_width+10,
                 font=self.main_label_font).grid(row=row,
                                                 column=column,
                                                 padx=(10, 0),
                                                 sticky='w',
                                                 pady=self.y_pad)
        entry_object = ttk.Entry(parent_obj, width=30, font=self.main_label_font)
        entry_object.insert('0', tv)
        entry_object.grid(row=row+1, column=column, padx=(0, 10), pady=self.y_pad)

        return entry_object

    def _walk_community(self, communities, tree, parent_obj=''):
        for c in communities:
            print("C: " + str(c))
            obj = tree.insert(parent_obj, index='end', text=c.get('name'))

            for co in c.get('collection'):
                tree.insert(obj, index='end', text=co.get('name'), tags='collection', values=co['id'])
                print("Co: " + str(co))

            if len(c.get('community')) > 0:
                print("Recursive")
                self._walk_community(c.get('community'), tree, obj)


    def _populate_dspace_tree(self, dspace_host, trees):
        response = requests.get(dspace_host + '/rest/hierarchy', verify=False)
        c = response.json().get('community')

        # Make sure trees are empty before populating
        for t in trees:
            t.delete(*t.get_children())
            self._walk_community(c, t)
            t.tag_configure('collection', font=('Arial', '14', 'bold'))


    def on_click(self, event):
        tree = event.widget
        print(tree)
        item_name = tree.identify_row(event.y)
        print(item_name)
        if item_name:
            tags = tree.item(item_name, 'tags')
            if tags and ('collection' in tags or 'archival_object' in tags):
                tree.selection_set(item_name)


    def on_click2(self, event, dcterms_combobox, dcterms_value):
        tree = event.widget
        print(tree)
        item_name = tree.identify_row(event.y)
        print(item_name)
        if item_name:
            values = tree.item(item_name, 'values')
            dcterms_combobox.set(values[0])
            dcterms_value.delete(0, tk.END)  # this will delete everything inside the entry
            dcterms_value.insert(tk.END, values[1])  # and this will insert the word "WORLD" in the entry

    def _populate_archivesspace_tree(self, host, repo, user, passw, tree):
        session = self.login(host, user, passw)
        resources = self.request(host, session.get, '/repositories/' + repo + '/resources', {'all_ids': True}, 200).json()

        for r in resources:
            as_tree = self.request(host, session.get, '/repositories/' + repo + '/resources/' + str(r) + '/tree', {}, 200).json()
            self.traverse_tree(tree, [as_tree])

    #@staticmethod
    def traverse_tree(self, tree, as_tree, parent_obj=''):
        #print(as_tree)
        for c in as_tree:
            print(c)
            if 'title' in c:
                obj = tree.insert(parent_obj, index='end', text=c['title'], tags='archival_object', values=c['id'])
                #print(str(i) + ' ' + c['title'])

            if 'children' in c:
                self.traverse_tree(tree, c['children'], obj)


    def add_metadata(self, tree, dcterms, dcterms_value):
        if isinstance(dcterms, ttk.Combobox):
            tree.insert('', index='end', values=(dcterms.get(), dcterms_value.get()))
        else:
            return tree.insert('', index='end', values=(dcterms, dcterms_value))


    def edit_metadata(self, tree, dcterms_combobox, dcterms_value):
        for s in tree.selection():
            tree.item(s, values=(dcterms_combobox.get(), dcterms_value.get()))

    def delete_metadata(self, tree, dcterms_combobox, dcterms_value):
        for s in tree.selection():
            tree.delete(s)

    def create_dspace_widgets(self, f1, f2, f3):
        # Content for DSpace AIP tree panel
        tree = ttk.Treeview(f1, selectmode='none', show='tree', columns=('Name', 'uuid'), displaycolumns=('Name'))
        # tree.bind("<<TreeviewSelect>>", self.treeview)
        # tree.pack(expand=tk.YES, fill=tk.BOTH)
        # tree.heading("#0", text="C/C++ compiler")
        tree.column("#0", minwidth=0, width=300)
        tree.column("Name", minwidth=0, width=300)
        tree.bind("<Button-1>", self.on_click)
        # tree.pack()
        tree.grid(row=0, column=0, rowspan=3, padx=(5, 5), pady=self.y_pad, sticky=tk.W)

        self.metadata.append(('dspace_aip_collection', tree))

        # Content for DSpace config panel
        row_count = 0
        dspace_aip_host = self.create_label_entry(f1, 'DSpace server:', row=row_count, column=1)


        ttk.Button(f1, text="Test connection",
                   command=lambda: self._populate_dspace_tree(dspace_aip_host.get(),
                                                              [tree, tree2])).grid(row=2,
                                                                                   column=1,
                                                                                   padx=(10, 5),
                                                                                   pady=self.y_pad,
                                                                                   sticky=tk.E)

        dspace_dip_host = self.create_label_entry(f2, 'DSpace server:', row=0, column=1)
        #row_count += 1

        archivesspace_host = self.create_label_entry(f3, 'ArchivesSpace server:', row=1, column=1, tv='http://lac-archives-test.is.ed.ac.uk:8089/')
        archivesspace_repo = self.create_label_entry(f3, 'ArchivesSpace repository:', row=3, column=1, tv='14')
        archivesspace_user = self.create_label_entry(f3, 'ArchivesSpace username:', row=5, column=1, tv='archivematica')
        archivesspace_passw = self.create_label_entry(f3, 'ArchivesSpace password:', row=7, column=1, tv='arch1vemat1ca')
        #row_count += 1
        #dspace_password = self.create_label_entry(f1, 'DSpace password:', row=row_count)
        row_count += 1
        ttk.Button(f2,
                   text="Test connection",
                   command=lambda: self._populate_dspace_tree(dspace_dip_host.get(),
                                                              [tree, tree2])).grid(row=2,
                                                                                   column=1,
                                                                                   padx=(10, 5),
                                                                                   pady=self.y_pad,
                                                                                   sticky=tk.E)
        ttk.Button(f3,
                   text="Test connection",
                   command=lambda: self._populate_archivesspace_tree(archivesspace_host.get(),
                                                                     archivesspace_repo.get(),
                                                                     archivesspace_user.get(),
                                                                     archivesspace_passw.get(),
                                                                     tree3)).grid(row=10,
                                                                                   column=1,
                                                                                   padx=(10, 5),
                                                                                   pady=self.y_pad,
                                                                                   sticky=tk.E)



        # Content for DSpace DIP tree panel
        tree2 = ttk.Treeview(f2, selectmode='none', show='tree', columns='Name')
        tree2.column("#0", minwidth=0, width=300)
        tree2.bind("<Button-1>", self.on_click)
        tree2.grid(row=0, column=0, rowspan=3, padx=(5, 5), pady=self.y_pad, sticky=tk.W)

        self.metadata.append(('dspace_dip_collection', tree2))

        # Content for DSpace DIP tree panel
        tree3 = ttk.Treeview(f3, selectmode='none', show='tree', columns='Name')
        tree3.column("#0", minwidth=0, width=300)
        tree3.bind("<Button-1>", self.on_click)
        tree3.grid(row=0, column=0, rowspan=10, padx=(5, 5), pady=self.y_pad, sticky=tk.W)

        self.metadata.append(('archivesspace_dip_collection', tree3))

        '''tree.insert('', 'end', 'widgets', text='Widget Tour')
        id = tree.insert('', 'end', text='Tutorial')
        id2 = tree.insert('', 'end', text='Tutorial2')
        tree.insert("", index="end", iid="Main", text="main branch")
        tree.insert("Main", index="end", text="Stuff 1")
        tree.insert("Main", iid="Main2", index="end", text="Stuff 2")
        tree.insert("Main2", index="end", text="Stuff 101")
        tree.insert("Main2", iid="Main12", index="end", text="Stuff 102")'''


    def create_widgets(self):
        ttk.Label(text='Package title:', width=self.main_label_width, font=self.main_label_font).grid(row=self.row_count, column=0, padx=(10, 0), pady=self.y_pad)
        package_title = ttk.Entry(width=40, font=('Arial', 18), validate="focusout", validatecommand=lambda: self._check_empty(package_title))
        package_title.grid(row=self.row_count, column=1, padx=(0, 10), pady=self.y_pad, columnspan=2)
        self.metadata.append(('dc.title', package_title))
        #self.non_empties.append(package_title)

        self.row_count += 1

        ttk.Label(text='Date:', width=self.main_label_width, font=self.main_label_font).grid(row=self.row_count, column=0, padx=(10, 0), pady=self.y_pad, sticky=tk.E)
        package_date = ttk.Entry(width=10, font=self.main_input_font, validate="focusout", validatecommand=lambda : self._check_empty(package_date))
        package_date.grid(row=self.row_count, column=1, padx=(5, 5), pady=self.y_pad, sticky=tk.W)
        ttk.Label(text='(DD/MM/YYYY)', width=22, font=('Arial', 12)).grid(row=self.row_count, column=2, padx=(0, 10), pady=self.y_pad, sticky=tk.W)
        self.metadata.append(('dc.date.issued', package_date))

        self.row_count += 1

        ttk.Label(text='Author:', width=self.main_label_width, font=self.main_label_font).grid(row=self.row_count, column=0, padx=(10, 0),
                                                                                   pady=self.y_pad, sticky=tk.E)
        package_author = ttk.Entry(width=30, font=self.main_input_font)
        package_author.grid(row=self.row_count, column=1, padx=(5, 5), pady=self.y_pad, sticky=tk.W)
        #ttk.Label(text='?', width=12, font=('Arial', 12)).grid(row=self.row_count, column=2, padx=(0, 10), pady=self.y_pad, sticky=tk.W)
        self.metadata.append(('dc.creator', package_author))

        self.row_count += 1

        # Creating notebook and the three frames
        n = ttk.Notebook()
        f1 = ttk.Frame(n)
        f2 = ttk.Frame(n)
        f3 = ttk.Frame(n)
        f4 = ttk.Frame(n)
        f5 = ttk.Frame(n)
        n.add(f1, text='Metadata')
        n.add(f2, text='DSpace AIP Collection')
        n.add(f3, text='DSpace DIP Collection')
        n.add(f4, text='ArchivesSpace DIP link')
        n.add(f5, text='Submit')
        n.grid(row=self.row_count, column=0, columnspan=3, padx=(5, 5), pady=self.y_pad, sticky=tk.W)

        self.row_count += 1

        self.metadata_tree = ttk.Treeview(f1, selectmode='browse', columns=('#1', '#2'), show=["headings"])
        # tree.bind("<<TreeviewSelect>>", self.treeview)
        self.metadata_tree.grid(row=3, column=0, columnspan=2, rowspan=2, pady=self.y_pad)
        #tree.heading("#0", text="dcterm")
        #tree.column("#0", minwidth=0, width=100)
        self.metadata_tree.heading("#1", text="dcterms")
        self.metadata_tree.column("#1", minwidth=0, width=200)  #https://stackoverflow.com/questions/5286093/display-listbox-with-columns-using-tkinter
        self.metadata_tree.heading("#2", text="value")
        self.metadata_tree.column("#2", minwidth=0,
                    width=200)  # https://stackoverflow.com/questions/5286093/display-listbox-with-columns-using-tkinter
        #self.metadata_tree.bind("<Button-1>", (lambda x: self.on_click2(x, dcterms_combo, dcterms_value)))

        #self.add_metadata(tree, 'dc.title', 'A transfer title')

        ttk.Button(f1,
                   text='Edit',
                   command=lambda: self.edit_metadata(self.metadata_tree, dcterms_combo, dcterms_value)).grid(row=3,
                                        column=2,
                                        padx=(5, 10),
                                        pady=self.y_pad,
                                        sticky=tk.W)

        ttk.Button(f1,
                   text='Delete',
                   command=lambda: self.delete_metadata(self.metadata_tree, dcterms_combo, dcterms_value)).grid(row=4,
                                           column=2,
                                           padx=(5, 10),
                                           pady=self.y_pad,
                                           sticky=tk.W)

        #tree.insert('', index='end', values=('dcterms.author', 'test'))
        #tree.item()

        self.row_count += 1

        #sep = ttk.Separator(orient=tk.HORIZONTAL)
        #sep.grid(row=self.row_count, column=0, columnspan=3, pady=self.y_pad, sticky=tk.EW)

        ttk.Label(f1, text='DC Terms:', width=10, font=self.main_label_font).grid(row=0,
                                                                                  column=0,
                                                                                  padx=(10, 0),
                                                                                  pady=self.y_pad,
                                                                                  sticky=tk.E)

        dcterms_combo = ttk.Combobox(f1, width=50, font=self.main_input_font, values=self.dcterms)
        #print(isinstance(dcterms_combo, ttk.Combobox))
        dcterms_combo.grid(row=0, column=1, padx=(5, 5), pady=self.y_pad, sticky=tk.W)

        self.row_count += 1

        dcterms_value = ttk.Entry(f1, width=40, font=self.main_input_font)
        dcterms_value.grid(row=2, column=1, padx=(5, 5), pady=self.y_pad, sticky=tk.W)
        ttk.Button(f1, text='Add', command=lambda : self.add_metadata(self.metadata_tree, dcterms_combo, dcterms_value)).grid(row=2,
                                    column=2,
                                    padx=(5, 10),
                                    pady=self.y_pad,
                                    sticky=tk.W)


        self.create_dspace_widgets(f2, f3, f4)

        self.row_count = 0

        ttk.Button(f5, text='Select input directory', command=lambda: self._get_directory(self.input_dir, self.input_dir.label)).grid(row=self.row_count, column=0, padx=(10, 5), pady=self.y_pad, sticky=tk.E)
        self.input_dir = ttk.Entry(f5, width=40, font=self.main_input_font, validate="focusout", validatecommand=self._validate_input_dir)
        self.input_dir.grid(row=self.row_count, column=1, padx=(5, 10), pady=self.y_pad, sticky=tk.W)
        self.input_dir.label = ttk.Label(f5, text='?', width=22, font=('Arial', 12))
        self.input_dir.label.grid(row=self.row_count, column=2, padx=(0, 10), pady=self.y_pad, sticky=tk.W)
        #self.non_empties.append(self.input_dir)

        self.row_count += 1

        ttk.Button(f5, text='Select output directory', command=lambda: self._get_directory(self.output_dir)).grid(row=self.row_count, column=0, padx=(10, 5), pady=self.y_pad, sticky=tk.E)
        self.output_dir = ttk.Entry(f5, width=40, font=self.main_input_font)
        self.output_dir.grid(row=self.row_count, column=1, columnspan=2, padx=(5, 10), pady=self.y_pad, sticky=tk.W)
        self.non_empties.append(self.output_dir)

        self.row_count += 1

        ttk.Button(f5, text="Start transfer", command=self._start_transfer).grid(row=self.row_count, column=0, padx=(10, 5), pady=self.y_pad,
                                                                                        sticky=tk.E)
        ttk.Button(f5, text="Reset", command=self._reset).grid(row=self.row_count, column=1, padx=(5, 5),
                                                                                        pady=self.y_pad)
        ttk.Button(f5, text="Quit", command=root.destroy).grid(row=self.row_count, column=2, padx=(5, 10), pady=self.y_pad)
        #self.quit.pack(side="bottom")

    def _get_directory_size(self, dir):
        total_files = 0
        total_size = 0

        try:
            for subdir, dirs, files in os.walk(dir):
                for file in files:
                    full_filename = os.path.join(subdir, file)
                    total_files += 1
                    total_size += os.path.getsize(full_filename)
        except:
            messagebox.showerror('Error',
                                "Could not estimate total number and size of files in " + dir)

        return (total_files, total_size)

    def _validate_input_dir(self):
        #print(self._check_empty(self.input_dir))
        if self._check_empty(self.input_dir):
            for subdir, dirs, files in os.walk(self.input_dir.get()):
                for file in files:
                    full_filename = os.path.join(subdir, file)
                    print(full_filename)

            #self.input_dir.label.config(text=total_size)


    def _generate_json(self):
        test = { 'parts': 'objects/',
                 'dc.description.provenance': 'Submitted to Archivematica by ' + getpass.getuser() + " on computer "
                 + platform.node() + ' at ' + str(datetime.datetime.now())}

        for p in self.metadata:
            if len(p) == 2 and isinstance(p[1], ttk.Entry):
                print(p, p[0], p[1])
                test[p[0]] = p[1].get()
            elif len(p) == 2 and isinstance(p[1], ttk.Treeview):
                t_item = p[1].item(p[1].focus())
                #print(p[1].item(p[1].focus()))
                test[p[0]] = t_item['values'][0]
            else:
                print(p)

        return [test]

    def _check_empty(self, tk_obj):
        if len(tk_obj.get()) == 0:
            messagebox.showerror('Error', 'Error 1')
            tk_obj.config(background='red')
            return False
        else:
            #messagebox.showerror('Error', 'Error 2')
            #tk_obj.config(highlightbackground='white')
            return True


    def _check_errors(self, tk_obj):
        for t in tk_obj:
            v = t.get()
            if len(v) == 0:
                messagebox.showerror('Error', 'Error 2')
                t.config(background='red')
                return False

        return True

    def _reset(self):
        for p in self.metadata:
            p[1].delete(0, tk.END)

        self.input_dir.delete(0, tk.END)
        self.input_dir.label.config(text='')
        self.output_dir.delete(0, tk.END)
        #self.metadata = []


    def _start_transfer(self):
        if self._check_errors(self.non_empties) and messagebox.askokcancel("Confirm transfer?", "Do you want to start this transfer?\n" + self.input_dir.label.cget("text")):
            self._generate_json()
            self._copy_directory()
            #self._reset()


    def _copy_directory(self):
        try:
            input_dir = self.input_dir.get()
            output_dir = self.output_dir.get() + '/' + input_dir.split('/')[-1]
            shutil.copytree(input_dir, output_dir + '/objects/')

            os.mkdir(output_dir + '/metadata')

            with open(output_dir + '/metadata/metadata.json', 'w') as outfile:
                json.dump(self._generate_json(), outfile)
        except FileExistsError as e:
            print('Error: ' + e)
        except IOError as e:
            print('Error: ' + e)

        messagebox.showinfo('Transfer status', "Successfully copied from:\n\n" + input_dir + "\n\nto:\n\n" + output_dir)



    def _get_directory(self, text_obj, text_label=None):
        dir = tk.filedialog.askdirectory()
        text_obj.insert(tk.END, dir)

        if text_label is not None:
            files, size = self._get_directory_size(dir)
            size = str(size/(1024*1024.0))
            size = size[:size.find('.')+2]
            text_label.config(text="Files: " + str(files) + " Size: " + size + " mb")



root = tk.Tk()
root.title('Archive assistant')
#root.configure(background='beige')
root.resizable(width=0, height=0)

app = Application(master=root)

style = ThemedStyle(app)
style.theme_use("plastik")

# The themes plastik, clearlooks and elegance are recommended to make your UI look nicer on all platforms when using Tkinter and the ttk extensions in Python. When you are targeting Ubuntu, consider using the great radiance theme.

app.mainloop()