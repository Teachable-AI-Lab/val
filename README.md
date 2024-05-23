# val

First checkout the code:
```
git clone git@github.com:Teachable-AI-Lab/val.git
```

Once you checkout the code, navigate to the code folder and install it as a package:
```
pip install -e .
```

Once this is done, you should be able to try one of the test environments. You
can do this by naviagating to the `tests` folder. 

For example, to test VAL with overcooked, you can run:
```
python test_overcooked.py
```

This should open a pygame interface (sorry it is so buggy...) and you should be
able to teach it via the console.

If you want to run space transit, then you should start the unity game and then run:
```
python test_space_transit.py
```

If you would like to try the web-based interface, then do:
```
python val/user_interfaces/launch_server.py
```

Once you do this, you should be able to open your web browser to `http://localhost:4000` and see the UI.

Next, you can edit the `test_space_transit.py` file to comment out the line `user_interface = ConsoleUserInterface` and uncomment the line `# user_interface = WebInterface`.

Once you do this, you can launch unity and run:
```
python test_space_transit.py
```

You should now see all the interactions occur through the web browser page you opened. 
