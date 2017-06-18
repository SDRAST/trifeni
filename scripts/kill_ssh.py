from pyro4tunneling.util import kill_processes

if __name__ == '__main__':
    kill_processes('ssh', '-L')
